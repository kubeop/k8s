POOL_NAME=`hostname`
PS1_POOL=`echo ${POOL_NAME} | tr 'A-Z' 'a-z'`
PS1_INT=`/sbin/ip a | egrep -v 'inet6|127.0.0.1|\/32' | awk -F'[ /]+' '/inet/{print $NF" = "$3}' | head -n1`
export PS1='[\e[1;32m\u\e[m\e[1;33m@\e[m'"\e[1;35m$PS1_POOL\e[m"' \e[4m\w\e[m] \e[1;36m$PS1_INT\e[m\n\$ '


export HISTTIMEFORMAT="%Y-%m-%d:%H-%M-%S:`whoami`:  " 
alias vi=vim