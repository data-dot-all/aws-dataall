FROM public.ecr.aws/amazonlinux/amazonlinux:2023

ARG NODE_VERSION=18
ARG NVM_VERSION=v0.37.2
ARG PYTHON_VERSION=python3.9
ARG CONTAINER_USER=cuser
ARG CONTAINER_USER_GROUP=cuser
ARG CONTAINER_UID


# Clean cache
RUN dnf clean all

# Installing libraries
RUN dnf -y install -y \
    shadow-utils wget openssl-devel bzip2-devel libffi-devel \
    postgresql-devel gcc unzip tar gzip

# Install Python
RUN dnf install $PYTHON_VERSION
RUN dnf -y install python3-pip python3-devel git

RUN groupadd -r ${CONTAINER_USER_GROUP} && useradd -m -r -u ${CONTAINER_UID} -g ${CONTAINER_USER_GROUP} ${CONTAINER_USER}
RUN useradd -m app
RUN chown -R ${CONTAINER_USER}:root /usr/local
RUN chown -R ${CONTAINER_USER}:root /tmp

USER ${CONTAINER_USER}

## Add source
WORKDIR /build

# Configuring path
RUN touch ~/.bashrc

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

COPY --chown=${CONTAINER_USER}:root ./docker/dev/wait-for-it.sh /build/wait-for-it.sh
RUN chmod +x /build/wait-for-it.sh
RUN chown -R ${CONTAINER_USER}:root /build/wait-for-it.sh

## Add source
WORKDIR /dataall
RUN touch ~/.bashrc

# Configuring Node and CDK
RUN curl -o- https://raw.githubusercontent.com/creationix/nvm/$NVM_VERSION/install.sh | bash
RUN /bin/bash -c ". ~/.nvm/nvm.sh && \
	nvm install $NODE_VERSION && nvm use $NODE_VERSION && \
	npm install -g aws-cdk && \
	nvm alias default node && nvm cache clear"

RUN echo export PATH="\
/root/.nvm/versions/node/${NODE_VERSION}/bin:\
$(${PYTHON_VERSION} -m site --user-base)/bin:\
$(python3 -m site --user-base)/bin:\
$(python -m site --user-base)/bin:\
/home/${CONTAINER_USER}/.local/bin:\
$PATH" >> ~/.bashrc && \
     echo "nvm use ${NODE_VERSION} 1> /dev/null" >> ~/.bashrc

RUN /bin/bash -c  ". ~/.nvm/nvm.sh && cdk --version"

# App specific requirements
COPY ./requirements.txt requirements.txt
COPY ./dataall/base/cdkproxy/requirements.txt cdk.requirements.txt

# Install App requirements
RUN /bin/bash -c "${PYTHON_VERSION} -m pip install setuptools --prefix /usr/local"
RUN /bin/bash -c "${PYTHON_VERSION} -m pip install -r requirements.txt --prefix /usr/local"
RUN /bin/bash -c "${PYTHON_VERSION} -m pip install -r cdk.requirements.txt --prefix /usr/local"

# App code
COPY ./dataall /dataall
ADD ./cdkproxymain.py /cdkproxymain.py
ADD ./local_graphql_server.py /local_graphql_server.py

WORKDIR /

ENTRYPOINT [ "/bin/bash", "-c", ". ~/.nvm/nvm.sh && uvicorn cdkproxymain:app --host 0.0.0.0 --port 8080" ]
