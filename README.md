# PyEoD
Python Elemental on Discord is an implementation of [CaryKH's elemental 3](https://www.youtube.com/watch?v=J10KDPg_Im0) in python for a discord bot. We are opensource and are actively developing the bot, we encourage contributions and you can look below for the rules on contributing. 
[The bot invite link](https://discord.com/api/oauth2/authorize?client_id=1064270891464269854&permissions=277025705024&scope=bot%20applications.commands)
Please feel free to suggest new features, ideas, or bugs. All are welcome to submit issues to the github.
# Developing for PyEoD
## Code
* Do not write functions for code that will be only used once, at minimum split code into a function if it is repeated more than 2 times and you know 100% will not need to be changed (to your own knowledge of course)
* Write the simplest and easiest solution first, and then optimize it later
* Use [Black Python Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter) on everything you contribute
* model.py should stay completely in pure synchronous python, do not make multi-threaded or asynchronous changes to the backend without consulting more developers
* frontend.py should deal only with discord.py usage and other utility commands for interacting with the backend
* Do not assume you know best when changing older code, if a piece of code is more than 2 weeks old consult other developers before changing it
* Do not change the file structure unless given specific permission from Ray Chen, cheesy-brik,  or steyerofoam
## Github
* Commit <u>very often</u>
* Every commit you make should be a logical chunk or piece of code
* Commits should be self-tested and non-buggy, if you suspect bugs do not push to the branch and test it yourself
* Bugs that are not your own and that you have found should be reported to the issues tab
## Philosophy
* Features should be as easy as possible for users to use
* Obfuscation is ok if it makes something more accessible
* Duplicate features should not be used, but if a part of a feature is too annoying to use, making a shortcut to that feature is encouraged
* Suggestions made by users should be taken at high regard - __You do not know better than the users just because you know the code__
* Assume good faith when a person is suggesting or talking about a bug - __Do not be rude, aggressive, or dismissive of a new player or suggestions that are already in development
* If someone is confused take that as a sign to improve usability
* If enough of the community wants a feature, it is a good feature, the only reason it would not be is bad implementation
