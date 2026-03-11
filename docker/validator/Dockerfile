FROM python:3.12-slim

# System-level solvers — cannot be pip-installed
# Install IPOPT executable and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    coinor-ipopt \
    coinor-libipopt-dev \
    coinor-cbc \
    glpk-utils \
    gfortran \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python packages — the fixed, pre-approved set
RUN pip install --no-cache-dir \
    pyomo \
    cvxpy \
    casadi \
    scipy \
    numpy \
    sympy \
    pandas \
    matplotlib \
    control \
    slycot

WORKDIR /sandbox

# No network access at runtime — enforced by `docker run --network none`
# Code is mounted read-only at /sandbox via `-v <tmpdir>:/sandbox:ro`
