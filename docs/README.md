### 什么是Kubernetes 

​	Kubernetes是容器集群管理系统，是一个开源平台，可以实现容器集群的自动化部署、自动扩缩容、调度、维护等功能。通过Kubernetes你可以：

- 快速部署应用
- 快速扩展应用
- 无缝对接新的应用功能
- 节省资源，优化硬件资源利用率



### 为什么用kubernetes

​		Kubernetes能提供一个以容器为中心的分布式系统架构，以可移植、可缩放和可扩展的方式实现基于容器的环境。

- 可移植性

​       将容器化工作负载从本地开发计算机无缝移动到生产环境。在本地基础结构以及公有云、混合云或多云中，在不同环境中协调容器，保持一致性。

- 可伸缩性

​       定义复杂的容器化应用程序并将其全局部署在服务器群集甚至多个群集上 - 因为 Kubernetes 根据所需状态优化资源。Kubernetes 以水平方式扩缩应用程序时，会自动监视和维护容器运行状况。

- 可扩展性

​       访问由构建 Kubernetes 社区的开发者和公司创建的广域且不断增长的扩展和插件集合。可通过符合条件的 Kubernetes 服务充分利用这些社区产品/服务并添加安全性、监视和管理等功能。

- 自动化

​       自动部署、自动重启、自动复制、自动伸缩/扩展。



### kubernetes架构图

![CloudNativeLandscape_latest](https://feisky.gitbooks.io/kubernetes/architecture/images/architecture.png)





### kubernetes分层架构

![CloudNativeLandscape_latest](https://feisky.gitbooks.io/kubernetes/architecture/images/14937095836427.jpg)



- 核心层：kubernetes最核心的功能，对外提供API构建高层的应用，对内提供插件式应用执行环境
- 应用层：部署（无状态应用、有状态应用、批处理任务、集群应用等）和路由（服务发现、DNS解析等）
- 管理层：系统度量（如基础设施、容器和网络的度量），自动化（如自动扩展、动态Provision等）以及策略管理（RBAC、Quota、PSP、NetworkPolicy等）
- 接口层：kubectl命令行工具、客户端SDK以及集群联邦
- 生态系统：在接口层之上的庞大容器集群管理调度的生态系统，可以分为两个范畴
  - kubernetes外部：日志、监控、配置管理、CI、CD、Workflow、FaaS、OTS应用、ChatOps等
  - kubernetes内部：CRI、CNI、CVI、registry、Cloud Provider、集群自身的配置和管理等


