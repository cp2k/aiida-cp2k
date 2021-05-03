###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

FROM aiidateam/aiida-core:latest

# To prevent the container to exit prematurely.
ENV KILL_ALL_RPOCESSES_TIMEOUT=50

WORKDIR /opt/

# Install CP2K.
RUN apt-get update && apt-get install -y --no-install-recommends cp2k

# Install aiida-cp2k plugin.
COPY . aiida-cp2k
RUN pip install ./aiida-cp2k[pre-commit,test,docs,cli]

# Install coverals.
RUN pip install coveralls

# Install the cp2k code.
COPY .docker/opt/add-codes.sh /opt/
COPY .docker/my_init.d/add-codes.sh /etc/my_init.d/50_add-codes.sh
