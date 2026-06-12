from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from . import constants as C


class Regime(str, Enum):
    CALM = "CALM"
    VOLATILE = "VOLATILE"


def div_toward_zero(num: int, den: int) -> int:
    if den <= 0:
        raise ValueError("denominator must be positive")
    if num >= 0:
        return num // den
    return -((-num) // den)


def ema_update(basis_wad: int, obs_wad: int, dt_sec: int, tau_sec: int = C.TAU_SEC) -> int:
    if basis_wad == 0:
        return obs_wad
    if dt_sec == 0:
        return basis_wad
    k = (dt_sec * C.WAD) // (dt_sec + tau_sec)
    return basis_wad + ((obs_wad * k) // C.WAD) - ((basis_wad * k) // C.WAD)


def deviation_e2(mid_wad: int, fair_wad: int, basis_wad: int) -> tuple[int, int]:
    if mid_wad <= 0:
        raise ValueError("mid_wad must be positive")
    fair_local_wad = (fair_wad * basis_wad) // C.WAD
    dev_e2 = ((fair_local_wad * 1_000_000) // mid_wad) - 1_000_000
    return dev_e2, fair_local_wad


def is_correcting(dev_e2: int, zero_for_one: bool) -> bool:
    if dev_e2 > 0:
        return not zero_for_one
    if dev_e2 < 0:
        return zero_for_one
    return False


def premium_pips(
    abs_dev_e2: int,
    deadband_e2: int,
    alpha_num: int = C.ALPHA_NUM,
    alpha_den: int = C.ALPHA_DEN,
    cap_pips: int = C.CAP_PIPS,
) -> int:
    if abs_dev_e2 <= deadband_e2:
        return 0
    pips = ((abs_dev_e2 - deadband_e2) * alpha_num) // alpha_den
    return min(pips, cap_pips)


@dataclass(frozen=True)
class OracleSnapshot:
    fair_e18: int
    publish_time_ms: int
    price: int = 0
    conf: int = 0
    conf_e2: int | None = None

    def effective_conf_e2(self) -> int:
        if self.conf_e2 is not None:
            return self.conf_e2
        if self.price > 0:
            return (self.conf * 1_000_000) // self.price
        return 0


@dataclass(frozen=True)
class SwapInput:
    ts_ms: int
    pre_mid_e18: int
    post_mid_e18: int
    ab_e18: int
    aq_e6: int
    block_number: int | None = None
    tx_hash: str | None = None
    log_index: int | None = None

    @property
    def zero_for_one(self) -> bool:
        return self.ab_e18 > 0


@dataclass(frozen=True)
class Decision:
    label: str
    fair_e18: int | None
    publish_time_ms: int | None
    staleness_ms: int | None
    conf_e2: int | None
    dev_e2: int
    correcting: bool
    premium_pips: int
    extra_e6: int
    fallback_reason: str

    @property
    def charged(self) -> bool:
        return self.premium_pips > 0


@dataclass
class PipelineState:
    basis_wad: int = 0
    last_obs_t_ms: int = 0
    prev_mid_e18: int = 0
    conf_ema_e2: int = 0
    regime: Regime = Regime.CALM
    regime_expiry_ms: int = 0

    def effective_regime(self, ts_ms: int) -> Regime:
        if self.regime == Regime.VOLATILE and ts_ms <= self.regime_expiry_ms:
            return Regime.VOLATILE
        return Regime.CALM


@dataclass
class SignalPipeline:
    state: PipelineState = field(default_factory=PipelineState)
    tau_sec: int = C.TAU_SEC
    deadband_calm_e2: int = C.DEADBAND_CALM_E2
    deadband_vol_e2: int = C.DEADBAND_VOL_E2
    alpha_num: int = C.ALPHA_NUM
    alpha_den: int = C.ALPHA_DEN
    cap_pips: int = C.CAP_PIPS

    def set_volatile(self, now_ms: int, ttl_sec: int = C.REGIME_TTL_SEC) -> bool:
        expiry = now_ms + ttl_sec * 1000
        changed = self.state.regime != Regime.VOLATILE or expiry > self.state.regime_expiry_ms
        self.state.regime = Regime.VOLATILE
        self.state.regime_expiry_ms = max(self.state.regime_expiry_ms, expiry)
        return changed

    def expire_regime(self, now_ms: int) -> bool:
        if self.state.regime == Regime.VOLATILE and now_ms > self.state.regime_expiry_ms:
            self.state.regime = Regime.CALM
            self.state.regime_expiry_ms = 0
            return True
        return False

    def _max_staleness_ms(self, ts_ms: int) -> int:
        if self.state.effective_regime(ts_ms) == Regime.VOLATILE:
            return C.MAX_STALENESS_VOL_SEC * 1000
        return C.MAX_STALENESS_CALM_SEC * 1000

    def _deadband_e2(self, ts_ms: int) -> int:
        if self.state.effective_regime(ts_ms) == Regime.VOLATILE:
            return self.deadband_vol_e2
        return self.deadband_calm_e2

    def validate_oracle(self, swap: SwapInput, oracle: OracleSnapshot | None) -> tuple[bool, str, int | None, int | None]:
        if oracle is None:
            return False, "STALE_OR_MISSING", None, None
        if oracle.fair_e18 <= 0:
            return False, "BAD_PRICE", None, oracle.effective_conf_e2()
        staleness_ms = max(0, swap.ts_ms - oracle.publish_time_ms)
        conf_e2 = oracle.effective_conf_e2()
        if staleness_ms > self._max_staleness_ms(swap.ts_ms):
            return False, "STALE_OR_MISSING", staleness_ms, conf_e2
        if self.state.conf_ema_e2 != 0 and conf_e2 > self.state.conf_ema_e2 * C.CONF_ANOMALY_NUM:
            return False, "CONF_SPIKE", staleness_ms, conf_e2
        return True, "", staleness_ms, conf_e2

    def before_swap(self, swap: SwapInput, oracle: OracleSnapshot | None, label: str = "fresh") -> Decision:
        ok, reason, staleness_ms, conf_e2 = self.validate_oracle(swap, oracle)
        if not ok:
            return Decision(label, getattr(oracle, "fair_e18", None), getattr(oracle, "publish_time_ms", None), staleness_ms, conf_e2, 0, False, 0, 0, reason)
        if self.state.basis_wad == 0:
            return Decision(label, oracle.fair_e18, oracle.publish_time_ms, staleness_ms, conf_e2, 0, False, 0, 0, "BASIS_UNSEEDED")

        dev_e2, _ = deviation_e2(swap.pre_mid_e18, oracle.fair_e18, self.state.basis_wad)
        correcting = is_correcting(dev_e2, swap.zero_for_one)
        pips = 0
        extra_e6 = 0
        if correcting:
            pips = premium_pips(abs(dev_e2), self._deadband_e2(swap.ts_ms), self.alpha_num, self.alpha_den, self.cap_pips)
            extra_e6 = (abs(swap.aq_e6) * pips) // 1_000_000
        return Decision(label, oracle.fair_e18, oracle.publish_time_ms, staleness_ms, conf_e2, dev_e2, correcting, pips, extra_e6, "")

    def after_swap(self, swap: SwapInput, oracle: OracleSnapshot | None) -> str:
        ok, reason, _, conf_e2 = self.validate_oracle(swap, oracle)
        self.state.prev_mid_e18 = swap.post_mid_e18
        if not ok:
            return reason

        if self.state.conf_ema_e2 == 0:
            self.state.conf_ema_e2 = conf_e2 or 0
        else:
            self.state.conf_ema_e2 = (self.state.conf_ema_e2 * C.CONF_EMA_KEEP_NUM + (conf_e2 or 0)) // C.CONF_EMA_DEN

        obs = (swap.post_mid_e18 * C.WAD) // oracle.fair_e18
        if self.state.last_obs_t_ms == 0:
            dt_sec = 0
        else:
            dt_sec = (swap.ts_ms - self.state.last_obs_t_ms) // 1000
        self.state.basis_wad = ema_update(self.state.basis_wad, obs, dt_sec, self.tau_sec)
        self.state.last_obs_t_ms = swap.ts_ms
        return ""

    def process_swap(
        self,
        swap: SwapInput,
        decisions: dict[str, OracleSnapshot | None],
        update_oracle: OracleSnapshot | None,
    ) -> dict[str, Decision]:
        self.expire_regime(swap.ts_ms)
        result = {label: self.before_swap(swap, oracle, label) for label, oracle in decisions.items()}
        self.after_swap(swap, update_oracle)
        return result


@dataclass
class ReplayMetrics:
    rows: int = 0
    valid_rows: int = 0
    priced_rows: int = 0
    charged_rows: int = 0
    charged_agree_rows: int = 0
    premium_total_e6: int = 0
    premium_correct_e6: int = 0
    extra_e6: int = 0
    trailing_markout_e6: int = 0
    truth_markout_e6: int = 0
    dev_mae_e2: int = 0
    dev_median_err_e2: int = 0
    dev_p90_err_e2: int = 0

    @property
    def precision_bps(self) -> int:
        return ratio_bps(self.premium_correct_e6, self.premium_total_e6)

    @property
    def sign_agreement_bps(self) -> int:
        return ratio_bps(self.charged_agree_rows, self.charged_rows)

    @property
    def capture_truth_bps(self) -> int:
        return ratio_bps(self.extra_e6, abs(self.truth_markout_e6))


def ratio_bps(num: int, den: int) -> int:
    if den == 0:
        return 0
    return (num * 10_000) // den


def replay_event_result(
    basis_wad: int,
    prev_mid_e18: int,
    fair_e18: int,
    ab_e18: int,
    aq_e6: int,
    deadband_e2: int = C.DEADBAND_CALM_E2,
    alpha_num: int = C.ALPHA_NUM,
    alpha_den: int = C.ALPHA_DEN,
    cap_pips: int = C.CAP_PIPS,
) -> tuple[Decision, int]:
    if basis_wad == 0:
        return Decision("fixture", fair_e18, None, None, None, 0, False, 0, 0, "BASIS_UNSEEDED"), 0
    dev_e2, fair_local = deviation_e2(prev_mid_e18, fair_e18, basis_wad)
    zero_for_one = ab_e18 > 0
    correcting = is_correcting(dev_e2, zero_for_one)
    pips = premium_pips(abs(dev_e2), deadband_e2, alpha_num, alpha_den, cap_pips) if correcting else 0
    extra_e6 = (abs(aq_e6) * pips) // 1_000_000
    decision = Decision("fixture", fair_e18, None, None, None, dev_e2, correcting, pips, extra_e6, "")
    markout_e6 = div_toward_zero(ab_e18 * fair_local, 10**30) + aq_e6
    return decision, markout_e6


def replay_rows_exact(
    rows: list[dict],
    truth_rows: list[dict],
    include_quantiles: bool = True,
    alpha_num: int = C.ALPHA_NUM,
    alpha_den: int = C.ALPHA_DEN,
    cap_pips: int = C.CAP_PIPS,
    deadband_e2: int = C.DEADBAND_CALM_E2,
) -> ReplayMetrics:
    if len(rows) != len(truth_rows):
        raise AssertionError("truth length mismatch")

    basis_wad = 0
    last_obs_t_ms = 0
    prev_mid_e18 = 0
    metrics = ReplayMetrics(rows=len(rows))
    errors: list[int] = []

    for row, truth in zip(rows, truth_rows, strict=True):
        t_ms = int(row["t_ms"])
        if t_ms != int(truth["t_ms"]):
            raise AssertionError("truth t_ms mismatch")
        decision, markout_e6 = replay_event_result(
            basis_wad,
            prev_mid_e18,
            int(row["fair_e18"]),
            int(row["ab_e18"]),
            int(row["aq_e6"]),
            deadband_e2,
            alpha_num,
            alpha_den,
            cap_pips,
        )
        if truth.get("valid"):
            metrics.valid_rows += 1
            metrics.truth_markout_e6 += int(truth["truth_mk_e6"])
            if not decision.fallback_reason:
                metrics.priced_rows += 1
                metrics.extra_e6 += decision.extra_e6
                metrics.trailing_markout_e6 += markout_e6
                err = abs(decision.dev_e2 - int(truth["truth_dev_e2"]))
                errors.append(err)
                metrics.dev_mae_e2 += err
                if decision.charged:
                    metrics.charged_rows += 1
                    metrics.premium_total_e6 += decision.extra_e6
                    if int(truth["truth_corr"]) == 1:
                        metrics.charged_agree_rows += 1
                        metrics.premium_correct_e6 += decision.extra_e6

        obs = (int(row["p_e18"]) * C.WAD) // int(row["fair_e18"])
        dt = 0 if last_obs_t_ms == 0 else (t_ms - last_obs_t_ms) // 1000
        basis_wad = ema_update(basis_wad, obs, 1 if dt == 0 else dt)
        last_obs_t_ms = t_ms
        prev_mid_e18 = int(row["p_e18"])

    if errors:
        metrics.dev_mae_e2 //= len(errors)
        if include_quantiles:
            ordered = sorted(errors)
            metrics.dev_median_err_e2 = ordered[len(ordered) // 2]
            metrics.dev_p90_err_e2 = ordered[(len(ordered) * 90) // 100]
    return metrics


def median_int(values: Iterable[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median of empty sequence")
    return ordered[len(ordered) // 2]
