# LEGO-42114

sudo apt-get install pip
pip install buildhat

pip3 install pyPS4Controller
sudo apt update
sudo apt full-upgrade -y
sudo systemctl status bluetooth
hcitool dev
hcitool -i hci0 scan
bluetoothctl
sudo apt install libbluetooth-dev checkinstall pkg-config

In ~/.profile, at the end put
echo Running Lego Controller
python /home/lego/dumper/controller.py &
python /home/lego/dumper/controller.py &

why two times?
