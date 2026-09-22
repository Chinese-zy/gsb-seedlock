# seedlock

容器（入口命令不变）：

`docker build -t seedlock . && docker run --rm -p 8080:8080 seedlock`

- 种子是 `(APP_VERSION, sample.json 内容)` 的纯哈希派生值，构建时写进
  基础层的 `manifest.json`，不写进样例文件，运行期只读不改。
- 启动时核对进程内加载的版本、输入摘要、种子、基准输出；对不上则拒绝
  就绪（`/healthz` 返回 503）。
- `/healthz` 打进当前进程实跑两遍样例，要求逐字节一致且能复现清单，
  而不是只看端口/进程在不在。
- 容器内自检：`docker run --rm seedlock python3 server.py selfcheck`，
  任何一字节对不上都非零退出。
- 单测：`python3 -m unittest test_repro.py`。
