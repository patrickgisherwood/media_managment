#!/bin/bash

echo_msg(){
  MESSAGE=$1
  echo -e "\033[35m$MESSAGE\033[0m"
}

echo_warning(){
  MESSAGE=$1
  echo -e "\033[33m$MESSAGE\033[0m"
}


echo_error(){
  MESSAGE=$1
  echo -e "\033[31m$MESSAGE\033[0m"
}
