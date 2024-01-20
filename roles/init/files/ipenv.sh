PS1_POOL=$(echo ${HOSTNAME} | tr 'A-Z' 'a-z')
PS1_INT=$(/sbin/ip a | egrep -v 'inet6|127.0.0.1|\/32' | awk -F'[ /]+' '/inet/{print $NF" = "$3}' | head -n1)
export PS1='[\033[1;32m\u\033[0m\033[1;33m@\033[0m\033[1;35m$PS1_POOL\033[0m \033[1;91m\w\033[0m] \033[1;36m$PS1_INT\033[0m\n\$ '

export HISTTIMEFORMAT="%Y-%m-%d:%H-%M-%S:$(whoami):  "
alias vi=vim