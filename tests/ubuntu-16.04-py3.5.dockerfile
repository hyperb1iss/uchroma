FROM ubuntu:16.04
RUN apt-get update
RUN apt-get install -y software-properties-common python3-pip 
RUN add-apt-repository -s -y ppa:cyanogen/uchroma
RUN apt-get update
RUN apt-get build-dep -y uchroma
RUN python3 --version
RUN pip3 install --upgrade pip setuptools numpy pytest 

ADD . /root/
RUN cd /root && pip3 install . --upgrade
RUN cd /root && python3 setup.py build_ext --inplace
RUN cd /root && python3 setup.py hwdb
RUN cd /root && python3 -m pytest
