## 支持的发型版

- CentOS/RHEL 7，8
- Ubuntu 18.04，20.04
- Alma Linux 8
- Rocky Linux 8



## 支持组件

- Core
  - [kubernetes](https://github.com/kubernetes/kubernetes)
  - [etcd](https://github.com/etcd-io/etcd)
  - [containerd](https://github.com/containerd/containerd)
- Network Plugin
  - [cni-plugins](https://github.com/containernetworking/plugins)
  - [calico](https://github.com/projectcalico/calico)
  - [cilium](https://github.com/cilium/cilium)
  - [flanneld](https://github.com/flannel-io/flannel)
- Application
  - [coredns](https://github.com/coredns/coredns)
  - [metrics-server](https://github.com/kubernetes-sigs/metrics-server)
  - [kubernetes-dashboard](https://github.com/kubernetes/dashboard)
  - [helm](https://github.com/helm/helm)



## 部署要求

- **Minimum required version of Kubernetes is v1.21**
- Ansible v2.9.x, Jinja 2.11+ and python-netaddr is installed on the machine that will run Ansible commands
- The target servers must have **access to the Internet** in order to pull docker images. Otherwise, additional configuration is required
- The target servers are configured to allow **IPv4 forwarding**
- If using IPv6 for pods and services, the target servers are configured to allow **IPv6 forwarding**
- The **firewalls are not managed**, you'll need to implement your own rules the way you used to. in order to avoid any issue during deployment you should disable your firewall



## 基础配置

### 安装Ansible

```
pip3 install ansible==2.9.27
pip3 install netaddr -i https://mirrors.aliyun.com/pypi/simple/
```

- 如使用Python3，请在ansible.cfg的defaults配置下添加`interpreter_python = /usr/bin/python3`。



### 修改 inventory

请按照inventory模板格式修改对应资源

- 当haproxy和kube-apiserver部署在同一台服务器时，请确保端口不冲突。



### 配置 group_vars

编辑group_vars/all.yml文件，填入自己的配置。

请注意：

- 请尽量将etcd安装在独立的服务器上，不建议跟master安装在一起。数据盘尽量使用SSD盘。
- Pod 和Service IP网段建议使用保留私有IP段，建议（Pod IP不与Service IP重复，也不要与主机IP段重复，同时也避免与docker0网卡的网段冲突。）：
  - Pod 网段
    - A类地址：10.0.0.0/8
    - B类地址：172.16-31.0.0/12-16
    - C类地址：192.168.0.0/16
  - Service网段
    - A类地址：10.0.0.0/16-24
    - B类地址：172.16-31.0.0/16-24
    - C类地址：192.168.0.0/16-24



### 磁盘分区挂载

如已经自行格式化并挂载目录完成，可以跳过此步骤。

etcd数据盘

```
ansible-playbook fdisk.yml -i inventory -l etcd -e "disk=sdb dir=/var/lib/etcd"
```

containerd数据盘

```
ansible-playbook fdisk.yml -i inventory -l master,worker -e "disk=sdb dir=/var/lib/containerd"
```



## 部署集群

```
ansible-playbook cluster.yml -i inventory
```

如是公有云环境，使用公有云的负载均衡即可（需提前配置好负载均衡），无需安装haproxy和keepalived。

```
ansible-playbook cluster.yml -i inventory --skip-tags=haproxy,keepalived
```



## 扩容节点

### 扩容master节点

扩容时，请不要在inventory文件master组中保留旧服务器信息，仅保留扩容节点的信息。

格式化挂载数据盘

```
ansible-playbook fdisk.yml -i inventory -l ${SCALE_MASTER_IP} -e "disk=sdb dir=/var/lib/containerd"
```

执行生成节点证书

```
ansible-playbook cluster.yml -i inventory -t cert
```

执行节点初始化

```
ansible-playbook cluster.yml -i inventory -l ${SCALE_MASTER_IP} -t verify,init
```

执行节点扩容

```
ansible-playbook cluster.yml -i inventory -l ${SCALE_MASTER_IP} -t master,containerd,worker --skip-tags=bootstrap,create_worker_label
```



### 扩容node节点

扩容时，请不要在inventory文件worker组中保留旧服务器信息，仅保留扩容节点的信息。

格式化挂载数据盘

```
ansible-playbook fdisk.yml -i inventory -l ${SCALE_WORKER_IP} -e "disk=sdb dir=/var/lib/containerd"
```

执行生成节点证书

```
ansible-playbook cluster.yml -i inventory -t cert
```

执行节点初始化

```
ansible-playbook cluster.yml -i inventory -l ${SCALE_WORKER_IP} -t verify,init
```

执行节点扩容

```
ansible-playbook cluster.yml -i inventory -l ${SCALE_WORKER_IP} -t containerd,worker --skip-tags=bootstrap,create_master_label
```



## 替换集群证书

先备份并删除证书目录{{cert.dir}}，重新创建{{cert.dir}}，并将token、sa.pub、sa.key文件拷贝至新创建的{{cert.dir}}（这三个文件务必保留，不能更改），然后执行以下步骤重新生成证书并分发证书。

```
ansible-playbook cluster.yml -i inventory -t cert,dis_certs
```

然后依次重启每个节点。

重启etcd

```
ansible -i inventory etcd -m systemd -a "name=etcd state=restarted"
```

验证etcd

```
etcdctl endpoint health \
        --cacert=/etc/etcd/pki/etcd-ca.pem \
        --cert=/etc/etcd/pki/etcd-healthcheck-client.pem \
        --key=/etc/etcd/pki/etcd-healthcheck-client.key \
        --endpoints=https://172.16.90.101:2379,https://172.16.90.102:2379,https://172.16.90.103:2379
```

逐个删除旧的kubelet证书

```
ansible -i inventory -l master,worker -m shell -a "rm -rf /etc/kubernetes/pki/kubelet*"
```

- `-l`参数更换为具体节点IP。

逐个重启节点

```
ansible-playbook cluster.yml -i inventory -l ${IP} -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- 如calico、metrics-server等服务也使用了集群证书，请记得一起更新相关证书。
-  `-l`参数更换为具体节点IP。

重启网络插件

```
kubectl get pod -n kube-system | grep -v NAME | grep cilium | awk '{print $1}' | xargs kubectl -n kube-system delete pod
```
-  更新证书可能会导致网络插件异常，建议重启。
-  示例为重启cilium插件命令，请根据不同网络插件自行替换。



## 升级kubernetes版本

请先编辑group_vars/all.yml，修改kubernetes.version为新版本。

安装kubernetes组件

```
ansible-playbook cluster.yml -i inventory -t install_kubectl,install_master,install_worker
```

更新配置文件

```
ansible-playbook cluster.yml -i inventory -t dis_master_config,dis_worker_config
```

然后依次重启每个kubernetes组件。

```
ansible-playbook cluster.yml -i inventory -l ${IP} -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- `-l`参数更换为具体节点IP。

