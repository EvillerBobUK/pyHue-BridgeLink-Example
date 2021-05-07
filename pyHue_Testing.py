from time import sleep, time
from classes.pyHue_BridgeLink import pyHue_BridgeLink

bl = pyHue_BridgeLink("BridgeOne") # CHANGE THIS NAME TO MATCH YOUR CONFIG FILE
run_put_test = False
run_streaming_test_RGB = False
run_streaming_test_XYB = False


# UNCOMMENT THE OPTIONS BELOW, DEPENDING ON WHICH TEST YOU WANT
# TO RUN

run_put_test = True
#run_streaming_test_RGB = True
#run_streaming_test_XYB = True


if run_put_test == True:
    r = bl.put(bl.url,'lights/1/state',{"on":True,"xy":[0.6915,0.3083],"bri":254})
    print(r)
    r = bl.put(bl.url,'lights/2/state',{"on":True,"xy":[0.6915,0.3083],"bri":254})
    print(r)


if run_streaming_test_XYB == True:

    loop = 5   # Number of times to broadcast
    delay = 0.5 # How long to sleep between each broadcast

    bl.enable_streaming()

    while loop > 0:
        bl.prepare_and_send_broadcast(
            [
                (1, 0.6915,0.3083, 0.1),
                (2, 0.6915,0.3083, 0.1)
            ],'XYB'
        )
        delay(0.5)
        loop -= 1

    bl.disable_streaming()


if run_streaming_test_RGB == True:

    loop = 5    # Number of times to broadcast
    delay = 0.5 # How long to sleep between each broadcast

    bl.enable_streaming()

    while loop > 0:
        bl.prepare_and_send_broadcast(
            [
                (1, 255, 0, 0),
                (2, 255, 0, 0)
            ],'RGB'
        )
        sleep(delay)
        loop -= 1

    bl.disable_streaming()