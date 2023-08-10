import os

package = os.path.dirname(os.path.abspath(__file__))
control = os.path.join(package, "control")
stopfile = os.path.join(control, "stop")
restartfile = os.path.join(control, "restart")

# Debug server used to test new commands
main_server = 0
