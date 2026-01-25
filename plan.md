组件,设置项,推荐值,原因
MySQL (Docker),max-connections,1000,默认151不够你这台机器跑多进程并发。
MySQL (Docker),max_allowed_packet,64MB+,防止大文本/二进制写入报错。
Python ARQ,max_jobs,20,单进程并发数，内存充足可以大胆点。
Python DB,pool_size,20,必须 >= max_jobs，保证每个任务都有连接。
Python DB,pool_pre_ping,True,必开，防止空闲断连。
部署策略,进程数量,4 ~ 8 个,启动 4-8 个 ARQ 进程副本，榨干 8 张 GPU 和 128 核 CPU。
启动命令,日志重定向,> arq.log 2>&1,必须，否则 128 核产生的日志流会瞬间卡死 Screen。