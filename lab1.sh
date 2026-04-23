#!/bin/bash
g++ -c lab1.cpp
g++ -o lab1 lab1.o -lpthread
chmod +x ./lab1.sh
echo "Compiled successfully"
./lab1
