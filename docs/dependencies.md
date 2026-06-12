# Dependency pins

Dependencies are vendored under `lib/` for the public release so a fresh clone
can run `forge build && forge test` without installing submodules.

Original install command:

```bash
forge install --no-git foundry-rs/forge-std@v1.9.7 uniswap/v4-core@v4.0.0 uniswap/v4-periphery@363226d9e1e2180b67bf6857023dbaad751010c5
forge install --no-git reactive-lib=Reactive-Network/reactive-lib@v0.2.0
```

Pinned refs:

| Dependency | Ref | Commit |
|---|---:|---|
| `foundry-rs/forge-std` | `v1.9.7` | `77041d2ce690e692d6e03cc812b57d1ddaa4d505` |
| `uniswap/v4-core` | `v4.0.0` | `e50237c43811bd9b526eff40f26772152a42daba` |
| `uniswap/v4-periphery` | `363226d9e1e2180b67bf6857023dbaad751010c5` | `363226d9e1e2180b67bf6857023dbaad751010c5` |
| `Reactive-Network/reactive-lib` | `v0.2.0` | `d664678a7d86204c9391af4cedfd5ae0b0b904e4` |
