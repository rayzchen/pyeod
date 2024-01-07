import os

package = os.path.dirname(os.path.abspath(__file__))
package_location = os.path.dirname(package)
control = os.path.join(package, "control")
stopfile = os.path.join(control, "stop")
restartfile = os.path.join(control, "restart")

# Debug server used to test new commands
MAIN_SERVER = 0
SERVER_CONTROL_USERS = [
    663139761128603651,  # rayzchen
    666999744572293170,  # cheesybrik
    274518100500676608,  # steyerofoam
]
EMBED_COLOR = 0x3499EB
IMAGE_TYPES = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/bmp",
    "image/webp",
]
