import re


def get_netstring(string,netstring_end = ',', remove_netstring_encapsulation = True):
    """
    Searches for a netstrings inside string.  Returns the netstring and
    the string with the netstring and data preceeding the netstring
    removed. 
    Note that it will not find nested netstrings!

    """
    netstring_all = []
    string_crop = string
    while(True):
        m = re.search(r"\d+:",string_crop)
        if m is not None: # If we found a netstring
            # Convert the number of bytes into an int
            n = int(string_crop[m.span()[0]:m.span()[1]-1])
            # The length of the netstring part (number + : + netstring_end)
            n_netstr = m.span()[1] - m.span()[0]
            # delete the data before the netstring
            string_crop = string_crop[m.span()[0]:]
            # Do we have enough data in the string?
            if(len(string_crop) >= (n + n_netstr + 1)): 
                # print 'D',string[n+n_netstr]
                # If the last char is a netstring_end we have a valid netstring
                if(string_crop[n+n_netstr] == netstring_end):
                    if(remove_netstring_encapsulation):
                        netstring = string_crop[n_netstr:n+n_netstr]
                        string_crop = string_crop[n+n_netstr + 1:]
                    else:
                        netstring = string_crop[0:n+n_netstr + 1]
                        string_crop = string_crop[n+n_netstr:]   

                        
                    
                    netstring_all.append(netstring)
                else:
                    string_crop = string_crop[1:]
            else:
                break
        else:
            break

    return [string_crop,netstring_all]



if __name__ == '__main__':
    """
    Testing
    """

    send_strs = ["Hello, Hallo!","This is a test"]

    raw_string = ''
    for send_str in send_strs:
        raw_string += 'BLA' + str(len(send_str)) + ':' + send_str + ',' + 'BLUBBEL'
    
    print('raw string: ' + str(raw_string))
    [crop_string,netstrings] = get_netstring(raw_string,remove_netstring_encapsulation = True)
    print('Cropped string: ' + crop_string)
    for netstring in netstrings:
        print('Netstring: ' + netstring)    
    
