#!/bin/bash
set -e

# Este script se usa para corregir problemas con la red de nimbus por el MTU.

sh set-netplan-mtu-safe.sh
sh set-docker-mtu-safe.sh
sh create-sigicnetwork.sh
