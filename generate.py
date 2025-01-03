import yaml

# 读取 all.yml 文件 
with open('group_vars/all.yml', 'r', encoding='utf-8') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)

# 阿里云 ACR 镜像仓库信息
acr_repo = 'registry.cn-hangzhou.aliyuncs.com'
acr_namespace = 'kubeop'

images = {
    "quay.io/cilium/cilium": data['cilium']['version'],
    "docker.io/flannel/flannel": data['flannel']['version'],
    "docker.io/flannel/flannel-cni-plugin": data['flannel']['plugin_version'],
    "docker.io/calico/kube-controllers": data['calico']['version'],
    "docker.io/calico/node": data['calico']['version'],
    "docker.io/calico/cni": data['calico']['version'],
    "docker.io/cloudnativelabs/kube-router": data['kuberouter']['version'],
    "docker.io/coredns/coredns": data['coredns']['version'],
    "registry.k8s.io/dns/k8s-dns-node-cache": data['nodelocaldns']['version'],
    "registry.k8s.io/metrics-server/metrics-server": data['metrics_server']['version'],
    "registry.k8s.io/node-problem-detector/node-problem-detector": data['npd']['version'],
    "nvcr.io/nvidia/k8s-device-plugin": data['nvidia_device_plugin']['version']
}

credentials = {
    "docker.io": {
        "username": "${DKH_USERNAME}",
        "password": "${DKH_PASSWORD}"
    },
    "registry.cn-hangzhou.aliyuncs.com": {
        "username": "${ACR_USERNAME}",
        "password": "${ACR_PASSWORD}"
    }
}

def generate_images_yaml():
    # 写入仓库凭据信息
    with open('auth.yaml', 'w') as file:
        yaml.dump(credentials, file)
        file.write("\n")

    # 写入镜像信息
    for image, version in images.items():
        src_repo_url = f"{image}:{version}"
        dst_repo_url = f"{acr_repo}/{acr_namespace}/{image.split('/')[-1]}:{version}"
        print(f"Save {src_repo_url}: {dst_repo_url} to images.yaml")
        with open('images.yaml', 'a') as file:
            file.write(f"{src_repo_url}: {dst_repo_url}\n")

generate_images_yaml()