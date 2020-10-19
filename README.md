# dme-utils
Automates test transfers to/from endpoints used in the Data Mobility Exhibition (DME). Information on the datasets may be found at https://www.globusworld.org/tour/data-mobility-exhibition. DME endpoint definitions are stored in `dme_data.json`. Note that this file is not updated frequently so you may find that some endpoints are not currently active; if so, please try using a different entpoint.

## Usage Examples
#### Example 1: Transfer from a DME endpoint to your own endpoint
```bash
./rundme transfer --dataset ds10 --source 2 --non-dme-dest 924a32b0-6a2a-11e6-83a8-22000b97daec --dest-path my_dme_test/ds10 --create-path yes

Source endpoint name: cac_dtn_test
Source path: /datasets/ds10
Destination endpoint name: Some Test Endpoint
Destination path: /perftest/my_dme_test/ds10
Submitted transfer: be8fcec6-11d2-11eb-81b1-0e2f230cc907
Get transfer details by running 'rundme status --task-id be8fcec6-11d2-11eb-81b1-0e2f230cc907'
Visit the link below to see the changes: https://app.globus.org/app/file-manager?origin_id=606579ae-5b03-11e9-bf32-0edbf3a4e7ee&origin_path=%2Fdatasets%2Fds10&destination_id=924a32b0-6a2a-11e6-83a8-22000b97daec&destination_path=%2Fperftest%2Fmy_dme_test%2Fds10
```
Submits a transfer of dataset DS10 from DME endpoint #2 (as defined by the index in [`dme_data.json`](https://github.com/vasv/dme-utils/blob/main/dme_data.json)) to the endpoint with ID `924a32b0-6a2a-11e6-83a8-22000b97daec`. Files will be written to the `my_dme_test/ds10` subdirectory under the endpoint's writable root (usually `/perftest/` or `/globus/perftest`); check the resulting URL for the specific location. If the destination directory does not exist, it will be created before the transfer is submitted.

#### Example 2: Check the status of a transfer
```bash
./rundme status --task-id be8fcec6-11d2-11eb-81b1-0e2f230cc907
```
Prints details on the transfer with ID `be8fcec6-11d2-11eb-81b1-0e2f230cc907`.

#### Example 3: Transfer from your endpoint to a writable DME endpoint
``` bash
./rundme transfer --dataset ds10 --non-dme-source 924a32b0-6a2a-11e6-83a8-22000b97daec --dest 3 --dest-path uchicago/dme_test/ds10 --create-path yes
```
Submits a transfer of dataset DS10 from endpoint with ID `924a32b0-6a2a-11e6-83a8-22000b97daec` to DME endpoint #3 (as defined by the index in [`dme_data.json`](https://github.com/vasv/dme-utils/blob/main/dme_data.json)). Files will be written to the `uchicago/dme_test/ds10` subdirectory under the endpoint's writable root.
Note: the above requires that you have the specified dataset replicated on your endpoint.

#### Example 4: Transfer between two DME endpoints (mostly for calibration)
``` bash
./rundme transfer --dataset ds10 --source 2 --dest 1 --dest-path my_speed_test/ds10 --create-path yes
```
Submits a transfer of dataset DS10 from DME endpoint #2 (as defined by the index in [`dme_data.json`](https://github.com/vasv/dme-utils/blob/main/dme_data.json)) to DME endpoint #1. Files will be written to the `my_speed_test/ds10` directory under the endpoint's writable root.

## Shortcuts
You can add your own endpoints to the `dme_data.json` file so that you don't need to manually enter the UUID and paths for every transfer. For example, here we add an endpoint that is used as a destination only (and does not include the DME datasets):

``` bash
{
  ...
  {
    "index": "9",
    "id": "496e6d9e-d465-11e7-96b6-22000a8cbd7d",
    "name": "ESnet R/O - Sunnyvale",
    "writable": "1",
    "paths": {
      "dest": "/"
    }
  }
]
```
Now we can submit a transfer from dataset DS04 from DME endpoint #1 as follows:
``` bash
./rundme transfer --dataset ds04 --source 1 --dest 9 --dest-path uchicago/esnet_test/ds04
Source endpoint name: cac_dtn_test
Source path: /datasets/ds04
Destination endpoint name: ESnet write test endpoint at Sunnyvale
Destination path: /uchicago/esnet_test/ds04
Submitted transfer: ee7c6310-124f-11eb-893d-0a5521ff3f4b
Get transfer details by running: ./rundme status --task-id ee7c6310-124f-11eb-893d-0a5521ff3f4b
Visit the link below to see the changes: https://app.globus.org/app/file-manager?origin_id=606579ae-5b03-11e9-bf32-0edbf3a4e7ee&origin_path=%2Fdatasets%2Fds04&destination_id=496e6d9e-d465-11e7-96b6-22000a8cbd7d&destination_path=%2Fuchicago%2Fesnet_test%2Fds04
```
Note: The above omits the `--create-path` option; assumes that the `uchicago/esnet_test/ds04` directory already exists on the destination endpoint under the writable root.
