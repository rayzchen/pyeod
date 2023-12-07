import os

package = os.path.dirname(os.path.abspath(__file__))
package_location = os.path.dirname(package)
control = os.path.join(package, "control")
stopfile = os.path.join(control, "stop")
restartfile = os.path.join(control, "restart")

# Debug server used to test new commands
main_server = 0

embed_color = 0x3499EB
