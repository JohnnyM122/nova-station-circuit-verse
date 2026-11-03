#!/bin/bash
cd /home/ubuntu/NovaStation
source /home/ubuntu/BYOND/byond/bin/byondsetup
/home/ubuntu/BYOND/byond/bin/DreamMaker paradise.dme > /home/ubuntu/compile.log 2>&1
echo "EXIT_CODE=$?" >> /home/ubuntu/compile.log
