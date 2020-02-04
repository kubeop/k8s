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



### Kubernetes组件

**master节点：**

- **etcd**：

  一致性的KV存储系统，保存了整个集群的状态。除了具备状态存储的功能，还有事件监听和订阅、Leader选举的功能，所谓事件监听和订阅，各个其他组件通信，都并不是互相调用 API 来完成的，而是把状态写入 etcd（相当于写入一个消息），其他组件通过监听 etcd 的状态的的变化（相当于订阅消息），然后做后续的处理，然后再一次把更新的数据写入 etcd。所谓 Leader 选举，其它一些组件比如 Scheduler，为了做实现高可用，通过 etcd 从多个（通常是3个）实例里面选举出来一个做Master，其他都是Standby。

- **apiserver**：

  刚才说了 etcd 是整个系统的最核心，所有组件之间通信都需要通过 etcd，实际上，他们并不是直接访问 etcd，而是访问一个代理，这个代理是通过标准的RESTFul API，重新封装了对 etcd 接口调用，K8S里所有资源的增、删、改、查等操作，除此之外，这个代理还实现了一些附加功能，比如身份的认证、访问控制、API注册、发现、缓存等。这个代理就是 API Server。

- **controller manager**：

  kubernetes里所有资源对象的自动化控制中心，可以理解为资源对象的"大总管"。每一个任务请求发送给Kubernetes 之后，都是由 Controller Manager 来处理的，每一个任务类型对应一个 Controller Manager。

- **scheduler**：

  负责资源的调度，Controller Manager 会把任务对资源要求，其实就是 Pod，写入到 etcd 里面，Scheduler 监听到有新的资源需要调度（新的 Pod），就会根据整个集群的状态，给 Pod 分配到具体的节点上，相当于公交公司的"调度室"。

**node节点：**

- **kubelet**：

  是一个 Agent，运行在每一个节点上，它会监听 etcd 中的 Pod 信息，发现有分配给它所在节点的 Pod 需要运行，就在节点上运行相应的 Pod，并且把状态更新回到 etcd。维护容器的生命周期，同时也负责Volume（CVUI）和网络（CNI）的管理。

- **kube-proxy**：

  负责为Service提供Cluster内部的服务发现和负载均衡

- **container runtime**：

  负责镜像管理以及Pod和容器的真正运行（CRI）

**除了核心组件，还有一些推荐的Add-ons：**

- coredns：

  负责为整个集群提供DNS服务

- ingress controller：

  为服务提供外网入口

- heapster：

  提供资源监控，逐步被放弃，被metrics-server代替

- metrics-server：

  metrics Server 是集群范围资源使用数据的聚合器，用来替换heapster

- dashboard：

  提供GUI

- federation：

  提供跨可用区、跨云的多集群管理

- fluentd-elasticsearch：

  提供集群日志采集、存储与查询

- prometheus：

  提供集群的监控采集与查询


