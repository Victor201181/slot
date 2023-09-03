#!/bin/bash

# Задание:
# Написать необходимые скрипты и конфиги, удовлетворяющие следующим требованиям:
# 1. Реализовать фаервол на iptables, в котором будет разделение на цепочки(chain) по указанным
# критериям:
# цепочка для адресов, которым разрешено все (все порты)
# цепочка для адресов серверов баз данных и контейнеров с приложением, которым разрешено все
# цепочка, в которую будут заноситься адреса пользователей, которым нужен доступ по требованию. Им также
# разрешено все
# цепочка, в которую будут заноситься адреса пользователей с временным доступом, им разрешены только
# определенные порты
# цепочка, в которую заносятся порты, смотрящие в мир
# остальной траффик блокируем и все что блокируем - логируем. Для каждой цепочки организовать свой файл лога. В
# выводе iptables -L каждый добавленный адрес должен быть подписан именем

function ENTER-IP() {
	echo -n "Enter a IP address(example 10.10.10.10): "
	read IP
}

function ENTER-PORT() {
	echo -n "Enter a PORT(example: tcp, udp, all, 8080): "
	read PORT
}

# # цепочка для адресов, которым разрешено все (все порты)
# iptables -N chain-address-all-accept
# iptables -A chain-address-all-accept -p all -s 192.168.1.148 -j ACCEPT -m comment --comment "ADD in $CHAIN IP address - $IP"

function chain-address-all-accept() {
	echo "--- --- --- --- --- --- ---"
	echo "CHAIN=chain-address-all-accept"
	CHAIN="chain-address-all-accept"
	echo "--- --- --- --- --- --- ---"
	ENTER-IP
	echo "--- --- --- --- --- --- ---"
	echo "IP=$IP"
	IP="$IP"
	echo "--- --- --- --- --- --- ---"
	sudo iptables -N $CHAIN
	sudo iptables -A $CHAIN -p all -s $IP -j ACCEPT -m comment --comment "ADD in $CHAIN IP address - $IP"
	echo "ADD in iptables rule"
	chain-log
	echo "ADD log in /var/log/$CHAIN.log"
	drop-log
}

# # цепочка для адресов серверов баз данных и контейнеров с приложением, которым разрешено все
# iptables -N chain-db-containers-accept
# iptables -A chain-db-containers-accept -p all -s 192.168.1.148 -j ACCEPT

function chain-db-containers-accept() {
	echo "--- --- --- --- --- --- ---"
	echo "CHAIN = chain-db-containers-accept"
	CHAIN="chain-db-containers-accept"
	echo "--- --- --- --- --- --- ---"
	ENTER-IP
	echo "--- --- --- --- --- --- ---"
	echo "IP = $IP"
	IP="$IP"
	echo "--- --- --- --- --- --- ---"
	sudo iptables -N $CHAIN
	sudo iptables -A $CHAIN -p all -s $IP -j ACCEPT -m comment --comment "ADD in $CHAIN IP address - $IP"
	echo "ADD in iptables rule"
	chain-log
	echo "ADD log in /var/log/$CHAIN.log"
	drop-log
}

# # цепочка, в которую будут заноситься адреса пользователей, которым нужен доступ по требованию. Им также
# # разрешено все
# iptables -N chain-access-on-demand-accept
# iptables -A chain-access-on-demand-accept -p all -s 192.168.1.148 -j ACCEPT

function chain-access-demand-accept() {
	echo "--- --- --- --- --- --- ---"
	echo "CHAIN = chain-access-demand-accept"
	CHAIN="chain-access-demand-accept"
	echo "--- --- --- --- --- --- ---"
	ENTER-IP
	echo "--- --- --- --- --- --- ---"
	echo "IP = $IP"
	IP="$IP"
	echo "--- --- --- --- --- --- ---"
	sudo iptables -N $CHAIN
	sudo iptables -A $CHAIN -p all -s $IP -j ACCEPT -m comment --comment "ADD in $CHAIN IP address - $IP"
	echo "ADD in iptables rule"
	chain-log
	echo "ADD log in /var/log/$CHAIN.log"
	drop-log
}

# # цепочка, в которую будут заноситься адреса пользователей с временным доступом, им разрешены только
# # определенные порты
# iptables -N chain-temp-access-spec-ports
# iptables -A chain-temp-access-spec-ports -p tcp -s 192.168.1.148 --dport 7777 -j ACCEPT

function chain-temp-access-spec-ports() {
	echo "--- --- --- --- --- --- ---"
	echo "CHAIN = chain-temp-access-spec-ports"
	CHAIN="chain-temp-access-spec-ports"
	echo "--- --- --- --- --- --- ---"
	ENTER-IP
	echo "--- --- --- --- --- --- ---"
	echo "IP = $IP"
	IP="$IP"
	echo "--- --- --- --- --- --- ---"
	ENTER-PORT
	echo "--- --- --- --- --- --- ---"
	echo "PORT = $PORT"
	sudo iptables -N $CHAIN
	sudo iptables -A $CHAIN -p tcp -s $IP --dport $PORT -j ACCEPT -m comment --comment "ADD in $CHAIN IP address - $IP"
	echo "ADD in iptables rule"
	chain-log
	echo "ADD log in /var/log/$CHAIN.log"
	drop-log
}

# # цепочка, в которую заносятся порты, смотрящие в мир
# iptables -N chain-ports-inet
# iptables -A chain-ports-inet
# iptables -A <chain-name> -p tcp -m state --state NEW -m tcp --dport 80,443,8080 -j ACCEPT

function chain-ports-inet() {
	echo "--- --- --- --- --- --- ---"
	echo "CHAIN = chain-ports-inet"
	CHAIN="chain-ports-inet"
	echo "--- --- --- --- --- --- ---"
	ENTER-PORT
	echo "--- --- --- --- --- --- ---"
	echo "PORT = $PORT"
	PORT="$PORT"
	sudo iptables -N $CHAIN
	sudo iptables -A $CHAIN -p tcp -m state --state NEW -m tcp --dport $PORT -j ACCEPT -m comment --comment "ADD in $CHAIN PORT address - $PORT"
	echo "ADD in iptables rule"
	chain-log
	echo "ADD log in /var/log/$CHAIN.log"
	drop-log
}

# Для каждой цепочки организовать свой файл лога.

function chain-log() {
	sudo iptables -A $CHAIN -j NFLOG --nflog-prefix "iptables: " --nflog-group 30
	sudo ulogd -d -l /var/log/$CHAIN.log
}
# остальной траффик блокируем и все что блокируем - логируем. 

function drop-log() {
	sudo iptables -N DROP_LOGGING
	sudo iptables -A INPUT -j DROP_LOGGING
	# iptables -A OUTPUT -j LOGGING
	sudo iptables -A DROP_LOGGING -m limit --limit 2/min -j LOG --log-prefix "IPTables-Dropped: " --log-level 4
	sudo iptables -A DROP_LOGGING -j DROP
}

function manageMenu() {
	echo "--- --- --- --- --- --- ---"
	echo "Welcome to ADD CHAIN IPTABLES!"
	echo "--- --- --- --- --- --- ---"
	echo "What do you want to do?"
	echo "   1) Add chain-address-all-accept - цепочка для адресов, которым разрешено все (все порты)"
	echo "   2) Add chain-db-containers-accept - цепочка для адресов серверов баз данных и контейнеров с приложением, которым разрешено все"
	echo "   3) Add chain-access-demand-accept - цепочка, в которую будут заноситься адреса пользователей, которым нужен доступ по требованию. Им разрешено все"
	echo "   4) Add chain-temp-access-spec-ports - цепочка, в которую будут заноситься адреса пользователей с временным доступом, им разрешены только определенные порты"
    echo "   5) Add chain-ports-inet - цепочка, в которую заносятся порты, смотрящие в мир"
	echo "   6) Exit"
	until [[ ${MENU_OPTION} =~ ^[1-6]$ ]]; do
		read -rp "Select an option [1-6]: " MENU_OPTION
	done
	case "${MENU_OPTION}" in
	1)
		chain-address-all-accept
		;;
	2)
		chain-db-containers-accept
		;;
	3)
		chain-access-demand-accept
		;;
	4)
		chain-temp-access-spec-ports
		;;
    5)
		chain-ports-inet
		;;
	6)
		exit 0
		;;
	esac
}

manageMenu