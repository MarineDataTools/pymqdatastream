#
# 
# 
#
#
# 
#
import sys
import argparse
import logging

# Definitions
IND_FSIZE = [3,11]
IND_LASTSECTOR = [15,18]


class todlfs():
    """ An object to handle the todlfs filesystem, either saved in a file, or directly from the device
    device_type: "file" or "serial"
    """
    def __init__(self,device,device_type="file"):
        self.device = device
        if(device_type == "file"):
            self.get_sector = self.get_sector_file
            print('Opening:' + str(device))
            self.f = open(device,'rb')
        elif(device_type == "serial"):
            self.get_sector = self.get_sector_serial
            self.f = None


        self.firstsec = self.get_sector(0)
        self.secondsec = self.get_sector(1)

        self.check_fs()
    def check_fs(self):
        """ Checks if we really have a todlfs here
        """
        # Read the first free sector
        try:
            self.first_free_sector = int.from_bytes(self.firstsec[0:4], byteorder='big')
            self.num_sectors = self.first_free_sector - 1
            print('Num sectors:' + str(self.num_sectors))
        except Exception as e:
            print('Exception:' + str(e))
            self.is_todlfs = False
        

        return True
    def get_sector_file(self,sectors):
        """Reads sectors from file, this function is linked to
        self.get_sector()

        """
        data = []
        FLAG_INT = False
        # If sector is just an int
        if type(sectors) == int:
            sectors = [sectors]
            FLAG_INT = True
        elif(type(sectors) == list):
            pass
        else:
            print('Argument should be int/list,exiting')
            return

        for i in sectors:
            self.f.seek(i*512)
            data.append(self.f.read(512))

        # returns 
        if FLAG_INT:
            return data[0]

        

    def get_sector_serial(self,sectors):
        pass

    def list_files(self):
        pass



print(__name__)
if __name__ == "__main__":
    print('Hallo')
    tfs = todlfs("example/todl2_dep8.todlfs","file")
    print(tfs.firstsec)

    
