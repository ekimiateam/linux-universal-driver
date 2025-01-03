# Linux Universal Driver

This program installs drivers and provides restore functionality for linux powered
machines.

This software is based on system76-driver project ( Thanks to them ! )

It is only used currently on https://ekimia.fr/linuxuniversaldriver/

#Supported machines 

| Factory  | Manufacturer     | Board Name        | Product Name     |
|----------|------------------|-------------------|------------------| 
| Apple?   | Apple            | MacBookAir6,2     | macbookair62     |
| Apple?   | Apple            | MacBookAir7,2     | macbookair72     |
| Clevo    | System76         | Any               | Any              |
| Tongfang | Ekimia           | PH4TRX1           | fox1             |
| Clevo    | Ekimia           | NS50_70MU         | jaguar1/leopard1 | 
| Clevo    | Ekimia           | NS5x_NS7xPU       | jaguar2/leopard2 |
| Clevo    | Ekimia           | NS5x_NS7xAU       | jaguar3/leopard3 |
| Clevo    | Ekimia           | NP5x_NP7xHH_HJ_HK | guerilla1        |
| Clevo    | Ekimia           | NL40_50CU         | pulsar1/polar1   |
| Clevo    | Ekimia           | NL4x_NL5xLU       | pulsar2/polar2   |
| Clevo    | Ekimia           | NLx0MU            | pulsar3/polar3   |
| Clevo    | Ekimia           | NLxxPUx           | pulsar4/polar4   |
| Clevo    | Ekimia           | L141CU            | neutron1         |
| Clevo    | Ekimia           | L141MU            | neutron2         |
| Clevo    | Ekimia           | L140PU            | neutron3         |
| Tongfang | Ekimia           | GM5HG0A           | fusion1          |
| Tongfang | Ekimia           | GX4HRXL           | kevlar.amd       |
| Tongfang | Ekimia           | GX4MRXL           | kevlar.intel     |











# Using LUD

You can start quickly the GUI by double cliking ( or launch as a program ) on startlud.sh

Or once installed : 

Launch the 'LUD' application and enter your password to open the application.

## Making changes

1. Checkout new branch
2. Push new branch
3. Bump the version (`./bump-version.py`)
4. Make changes
5. Make pull request
6. Get PR approved and merged
7. Make a release from master branch (`./make-release.py`)

## License

This software is made available under the terms of the GNU General Public
License; either version 2 of the License, or (at your option) any later
version. See [LICENSE](LICENSE) for details.
