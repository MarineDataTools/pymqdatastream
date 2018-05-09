#
# First Sector
# Bytes 0:4: uint32 first free sector
#
#
# File: 
#
import sys
import os
import argparse
import logging

# Definitions
IND_FSIZE = [3,11]
IND_LASTSECTOR = [15,18]

todl_data = '/home/holterma/tmp/data/'
todl_data_split = '/home/holterma/tmp/data_split/'
todl_fname = 'todl_data_2017-07-24:05:43:27.todl'
todl_fname = 'todl_data_2017-07-31:12:36:24.todl' # Transcoast data
#todl_fname = 'todl_data_2017-07-31:12:43:18.todl' # Transcoast data
todl_fname = 'todl_data_2017-10-08:13:30:42.todl' # EMB169 v0.76 logger test
todl_fname = 'todl_data_2017-10-09:08:51:45.todl' # EMB169 v0.77 logger test
todl_fname = 'todl_data_2017-10-09:09:08:05.todl' # EMB169 v0.77 short logger test
todl_fname = 'todl_data_2017-10-09:09:48:44.todl' # EMB169 test, freq 250
todl_fname = 'todl_data_2017-10-09:13:55:23.todl' # EMB169 test, freq 650
#todl_fname = 'todl_read.todlfs' # Bathtub test
todl_fname = 'todl_2.todlfs' # 
todl_fname = 'todl_bathtub.todlfs' # Bathtub test 2
todl_data_full = todl_data + todl_fname


def todlfs_scan(filename):
    """ Scans a todlfs dataset and returns available files
    """
    #logger.setLevel(loglevel)
    print('Opening file:' + str(filename))
    f = open(filename,'rb')
    data = f.read(512)
    # Read the first free sector
    first_free_sector = int.from_bytes(data[0:4], byteorder='big')
    num_sectors = first_free_sector - 1
    print('Num sectors:' + str(num_sectors))
    files = []
    
    # Get file information
    cur_sector = 2
    num_file = 0
    while(cur_sector < num_sectors):
        f.seek(cur_sector * 512)
        data_f = f.read(512)
        #print(data_f)
        #print(data_f[IND_FSIZE[0]:IND_FSIZE[1]])
        filesize = int.from_bytes(data_f[IND_FSIZE[0]:IND_FSIZE[1]], byteorder='big')
        first_file_sector = cur_sector
        last_file_sector = int.from_bytes(data_f[IND_LASTSECTOR[0]:IND_LASTSECTOR[1]], byteorder='big')
        print(' ')
        print(' ')        
        print('File:')
        print('Filesize:' + str(filesize) + ' last sector of file (in 512 byte steps):' + str(last_file_sector))
        ind = IND_LASTSECTOR[1]
        file_info = b''
        # This should basically work, but v0.78 and prior version have a bug not writing the "F"
        #file_name = file_info.split('@@F:')[1]
        # Look like this: @C:2017.10.21 10:39:04@@M:2017.10.22 07:09:29@@\x00:todl_data_000001.todl\x00
        # Should look like this: @C:2017.10.21 10:39:04@@M:2017.10.22 07:09:29@@F:todl_data_000001.todl\x00        
        # Lets read until we have a \x00 and many (2) @s        
        while(True):
            #print(str(data_f[ind]))
            if( (data_f[ind] == 0) and (data_f[ind+1] == 0x40) and (data_f[ind+2] == 0x40)):
                break            
            file_info += data_f[ind:ind+1]
            ind += 1

        print(last_file_sector)
        cur_sector = last_file_sector + 1        
        f.seek(cur_sector * 512)
        # Replace the missing F
        print(file_info)
        file_info = file_info.replace(b'\x00',b'F')
        print(file_info)        
        file_info = file_info.decode("utf-8")
        print('File info: ' + file_info)
        file_name = file_info.split('@@F:')[1]
        file_index = int(file_name.split('_')[0])
        
        # file_name = file_info.rsplit(':')[0]
        print('Num:' + str(num_file) + ' Filename:' + file_name)
        # 
        finfo = {'sstart':first_file_sector,'send':last_file_sector,'file_name':file_name,'filesize':filesize,'file_info':file_info}
        files.append(finfo)
        num_file += 1
        
    f.close()    
    return files


def todlfs_list():
    desc = 'Lists files within a todlfs data file.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('todlfs', help= 'The filename of the todlfs file')
    args = parser.parse_args()    
    filename  = args.todlfs    
    files = todlfs_scan(filename)    

def todlfs_get_files():
    usage_str = 'todlfs_get_files'
    desc = 'Splits a todlfs dump into the individual files. Example usage: ' + usage_str
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('todlfs', help= 'The filename of the todlfs file')
    parser.add_argument('data_folder',help='The folder in which the splitted files will be saved')
    parser.add_argument('index',help='Which files to be extracted',nargs='?')
    #parser.add_argument('deployment',help='The name of the deployment')        
    parser.add_argument('--verbose', '-v', action='count')

    args = parser.parse_args()
    # Print help and exit when no arguments are given
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
        
    #todl_fname = args.deployment
    filename  = args.todlfs
    todl_data_folder = args.data_folder

    if args.index == None:
        f_ind = None
    else:
        f_ind_tmp = args.index.split(',')
        f_ind = []
        for i in f_ind_tmp:
            f_ind.append(int(i))
            

    
    # Creating a data folder
    if not os.path.exists(todl_data_folder):
        print('Folder:' + todl_data_folder + ' does not exist, creating it')
        os.makedirs(todl_data_folder)
    else:
        print('Folder:' + todl_data_folder + ' exists, exiting')
        exit()
        
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG

    
    # Scan the todlfs dataset for files
    files = todlfs_scan(filename)
    
    # Write data to file
    if f_ind == None:
        f_ind = range(0,len(files))

    # Opening the file again
    f = open(filename,'rb')        
    for i in f_ind:
        finfo = files[i]
        print('Saving file' + str(finfo))
        file_info = b''
        f.seek(512 * (finfo['sstart'] + 1))
        file_data = f.read(( finfo['send'] - finfo['sstart'] ) * 512)
        file_name_full = todl_data_folder + '/' + finfo['file_name']
        print('Filename full:' + file_name_full)
        fsplit = open(file_name_full,'bw')
        fsplit.write(str(finfo['filesize']).encode('utf-8'))
        fsplit.write(b'@@@')
        fsplit.write(finfo['file_info'].encode('utf-8'))
        fsplit.write(b'\n')
        fsplit.write(file_data)
        fsplit.close()
    


#print(data)


