# seedlock

容器：`docker build -t seedlock . && docker run --rm -p 8080:8080 seedlock`。探活与复现要对齐版本和种子。

- 种子钉在独立镜像层（`seed.txt` 单独 `COPY`），运行期绝不回写；有效种子 = H(基础种子 | 加载版本 | 规范化输入)，不写进样例。
- 启动/探活校验进程实际加载的版本与镜像内 `VERSION` 一致，且该版本+该种子对样例输入连算两次逐字节相同，否则 `/healthz` 返回 503，容器 HEALTHCHECK 判不健康。
- 单测：`python3 test_repro.py`（逐字节一致、种子不被改、版本绑定、错版不就绪），差一字节即非零退出。
