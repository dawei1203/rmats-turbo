FROM debian:buster

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       cmake \
       cython \
       g++ \
       gfortran \
       git \
       libblas-dev \
       libgsl-dev \
       liblapack-dev \
       make \
       python-dev \
       python-numpy \
       r-base \
       r-cran-nloptr \
       zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* \
    # Use a build dir to be removed after artifacts are extracted
    && mkdir /rmats_build \
    && cd /rmats_build \
    && git clone https://github.com/Xinglab/rmats-turbo.git \
    && cd rmats-turbo \
    # The build will source setup_environment.sh which will source ~/.bashrc.
    # Skip that by truncating setup_environment.sh
    && echo '' > setup_environment.sh \
    # c++03 was the default for gcc 5.4.0.
    # Explicitly set the standard to build with newer gcc.
    && export CXXFLAGS="-std=c++03" \
    && ./build_rmats \
    # Copy the build results
    && mkdir /rmats \
    && cd /rmats \
    && cp /rmats_build/rmats-turbo/rmats.py ./ \
    && cp /rmats_build/rmats-turbo/cp_with_prefix.py ./ \
    && cp /rmats_build/rmats-turbo/*.so ./ \
    && mkdir rMATS_C \
    && cp /rmats_build/rmats-turbo/rMATS_C/rMATSexe ./rMATS_C \
    && mkdir rMATS_P \
    && cp /rmats_build/rmats-turbo/rMATS_P/*.py ./rMATS_P \
    && mkdir rMATS_R \
    && cp /rmats_build/rmats-turbo/rMATS_R/*.R ./rMATS_R \
    # Remove build dir
    && rm -rf /rmats_build

# Set defaults for running the image
WORKDIR /rmats
ENTRYPOINT ["python", "/rmats/rmats.py"]
CMD ["--help"]
