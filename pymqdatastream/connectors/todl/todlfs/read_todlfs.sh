#device=/dev/mmcblk0
device=/dev/sda
P=/home/holterma/peter.owncloud.holtermann.online/Documents/electronic/sam4log/todlfs/data
DATE=`date +%Y-%m-%d:%H:%M:%S`
filename=$P/todl_data_${DATE}.todl
echo "Reading data from $device into $filename"
dd if=$device of=$filename bs=512 count=1;

# Reads the first 4 bytes of filesystem to get the number of bytes
len=`od -A none --endian=big -N 4 -t u4 $filename`
len=$(($len + 1)) # Add 512 bytes
echo "Have to read $len 512 byte sectors"
dd if=$device of=$filename bs=512 count=$len;
