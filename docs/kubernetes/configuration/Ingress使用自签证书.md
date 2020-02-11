### 1、生成ca

准备证书生成文件ca.cnf

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]

[ v3_req ]
keyUsage = critical, cRLSign, keyCertSign, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:2
```

生成证书

```
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -days 1095 -out ca.pem \
        -subj "/CN=K8SRE/OU=SRE/config ca.cnf -extensions v3_req
openssl x509 -noout -text -in ca.pem
```



### 2、生成域名证书

准备证书生成文件client.cnf

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
```

生成证书

```
openssl genrsa -out client.key 4096

openssl req -new -key client.key -out client.csr -subj "/CN=ci.k8sre.com/OU=SER/s" -config client.cnf
  
openssl x509 -req -in client.csr -CA ca.pem -CAkey ca.key -CAcreateserial -extfile client.cnf -extensions v3_req
 
openssl x509 -noout -text -in client.pem
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr -subj "/CN=Jenkins TLS AUTH/OU=SOPC/s" -config client.cnf
```


### 3、转换证书

提供可以在mac等系统安装

```
openssl pkcs12 -export -in client.pem -inkey client.key -out client.p12 -name client
```


### 4、ingress配置

创建ingress 证书的secret

```
kubectl create secret generic jenkins --from-file=tls.crt=client.pem --from-file=ca.crt=ca.pem -n jenkins
```

ingress配置

```
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/auth-tls-secret: jenkins/jenkins
    nginx.ingress.kubernetes.io/auth-tls-verify-client: "on"
    nginx.ingress.kubernetes.io/auth-tls-verify-depth: "1"
  name: jenkins-master
  namespace: jenkins
spec:
  rules:
  - host: ci.k8sre.com
    http:
      paths:
      - backend:
          serviceName: jenkins-master
          servicePort: 8080
  tls:
  - hosts:
    - ci.k8sre.com
    secretName: jenkins
```

