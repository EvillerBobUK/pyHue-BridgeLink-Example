# pyHue-BridgeLink-Example
BridgeLink Example for help with debugging!

Requires you to have a Philips Hue Bridge v 2 and at least one compatible lightbulb

Tests are coded to assume lights 1 & 2

bridgeconfig.json needs to be updated with your bridge settings - the one included
here has placeholder gibberish which needs to be changed to your own userid/clientkey etc.

The mbedtls module used is from python-mbedtls which will also require mbedtls.
Both of these are on github but may require a bit of fiddling to install.
https://github.com/Synss/python-mbedtls
https://github.com/ARMmbed/mbedtls

The DTLS/PSK and struct packing was taken from another project on github:
https://github.com/asaril/hue-artnet