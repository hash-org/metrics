# Hash Compiler metrics laboratory

This repository contains a collection of tools that are used for measuring the performance 
of the Hash compiler across its development lifetime. In this repository, you will find the 
following tools:

- `bot` The GitHub bot that is used to automate the process of running performance tests during 
the development of the Hash compiler.

- `scripts` A collection of scripts that are used by the `bot` to run the performance tests.

- `store` An simple service that wraps the storage and retrieval of the performance tests through
an API. This wraps a basic DynamoDB application with a REST API to store and retrieve the performance.

- `web` the WEB UI that is used to visualise the performance tests.
