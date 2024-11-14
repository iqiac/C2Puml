FROM fedora:latest AS dev

# Install dependencies
RUN dnf upgrade -y && dnf install -y \
    sudo \
    make \
    zsh \
    tree \
    git \
    wget \
    tmux \
    helix \
    fzf \
    xclip \
    xsel
RUN dnf clean all && rm -rf /var/cache/dnf

# Add host user
ARG USER_NAME
ARG USER_UID
ARG USER_GID

RUN groupadd --gid ${USER_GID} ${USER_NAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USER_NAME} -s /bin/zsh
RUN echo "${USER_NAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup zsh shell with Oh-My-Zsh
USER ${USER_NAME}
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Download and install Miniconda non-interactively
RUN mkdir -p ~/miniconda3 \
    && wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh \
    && bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 \
    && rm ~/miniconda3/miniconda.sh

RUN source ~/miniconda3/bin/activate \
    && conda init --all \
    && conda config --set changeps1 false

ENV PATH="/home/${USER_NAME}/miniconda3/bin:$PATH"

# Update and install python packages
RUN conda install -y \
    -c conda-forge \
    pytest \
    pylint \
    black \
    isort
RUN conda update --all
