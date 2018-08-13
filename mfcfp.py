'''MODFLOW-CFP: writing input files & getting output data
Functions included:
ModflowCoc
ModflowCrch
ModflowCfp
cfp_write_input
update_nam
node_budget'''


##################################################

def ModflowCoc(nnodes,node_nums,n_nts,npipes,pipe_nums,t_nts=1):
    
    '''COC: CFP Output Control: Controls the nodes for which to print flow and head values, and the pipes for which to print flow rates and Reynolds numbers. 
Documentation: https://water.usgs.gov/nrp/gwsoftware/modflow2000/MFDOC/index.html?dis.htm
Note: no FloPy support for this file

Inputs:

nnodes: ds2 NNODES: integer for number of nodes to generate head & flow output for.
     output will be in separate files
    
node_nums: ds4 NODE_NUMBERS: list of integers for node numbers to generate output for. One node per line in FORTAN. 1-based indexing
    
n_nts: ds6 N_NTS: integer for time step interval to generate output for

npipes: ds8 NPIPES: integer for number of pipes to generate flow & Reynolds number output for (output will be in separate files)

pipe_nums: ds10 PIPE_NUMBERS: list of integers for pipe numbers to generate output for. One node per line in FORTRAN. 1-based indexing

t_nts: ds12 T_NTS: integer for time step interval to generate output for'''
    
    #FORTRAN comment lines to include:
    ds0 = '#COC file: Mode 1 time series output'   #ds0: required comment line
    ds1 = '#Number of nodes for output'  #ds1: required comment line 
    ds3 = '#Node numbers, one per line'  #ds3: required comment line
    ds5 = '#Output each n time steps'    #ds5: required comment line
    ds7 = '#Number of pipes for output'  #ds7: required comment line
    ds9 = '#Pipe numbers, one per line'  #ds9: required comment line
    ds11 = '#Output each n time steps'   #ds11: required comment line

    #Format inputs as strings for FORTRAN text file:
    nnodes_str = str(nnodes)        #convert to string
    node_nums_str = "\n".join([str(num) for num in node_nums]) #convert list to string, each item on new line
    n_nts_str = str(n_nts)          #convert to string
    npipes_str = str(npipes)        #convert to string 
    pipe_nums_str = "\n".join([str(num) for num in pipe_nums]) #convert list to string, each item on new line
    t_nts_str = str(t_nts)          #convert to string

    #Group into one dataset string:
    coc = [ds0,ds1,nnodes_str,ds3,node_nums_str,ds5,n_nts_str,
           ds7,npipes_str,ds9,pipe_nums_str,ds11,t_nts_str] 
    
    return coc


###################################################

def ModflowCrch(node_nums,spers,iflag_crch=1,p_crch=0):
    
    '''CRCH: CFP Recharge: Routes a fraction of diffuse recharge to conduit pipe nodes
Documentation: https://water.usgs.gov/nrp/gwsoftware/modflow2000/MFDOC/index.html?dis.htm
Note: No FloPy support available
Repeat entire dataset for each stress period

Inputs:

iflag_crch: ds1 IFLAG_CRCH: integer flag to activate CRCH. Repeat for each stress period. 
        # if not -1, node_nums & p_crch are read for each node in simulation
        # if -1, node_nums & p_crch from last stress period are used
        
node_nums: ds2 NODE_NUMBERS: (only if iflag_crch not -1), list of integers for node numbers, 1-based indexing, must include all nodes
    
p_crch: ds2 P_CRCH: list of floats for fraction of diffuse areal recharge (from RCH package) to partition directly into each conduit node. List 0 if none. Repeat for each stress period.
    
spers: array of stress period numbers from DIS file (1-based indexing)'''
    
    ds0 = 'IFLAG_RCH for stress period '  #ds0: required comment line - will repeat for each stress period
    
    #Format inputs as strings for FORTRAN text file:
    ds2 = []                                                             #initalize empty list
    for i in range(len(node_nums)):                                      #loop over nodes
        ds2.append(str(node_nums[i]) + ' ' + str(p_crch[i]))             #convert to list of string pairs
    ds2_str = "\n".join(ds2)                                             #convert list to string with each item on a new line

    #Group into one dataset string for all stress periods:
    crch = []
    for i in range(len(spers)):
        if iflag_crch[i] == 1:
            crch.append(ds0+str(spers[i]) + '\n' + str(iflag_crch[i]) + '\n' + ds2_str) #first sp
        else:
            crch.append(ds0+str(spers[i]) + '\n' + str(iflag_crch[i]))                  #all other sp
            
    return crch


############################################

def ModflowCfp(nnodes,npipes,nlay,network_info_file,geoheight_file,pipe_info_file,node_head_file,K_exch_file,
               mode=1,temp=25.0,sa_exch=1,epsilon=10e-6,niter=100,relax=1,p_nr=1):
    
    '''CFP: Primary conduit flow input - location, geometry, and properties of conduits
Documentation: https://water.usgs.gov/nrp/gwsoftware/modflow2000/MFDOC/index.html?dis.htm
Note: FloPy is not supported
Note: currently requires text files for arrays - next step is to create network info file from ArcMap data

Inputs:

mode: ds1 MODE: integer flag, 1 = pipes only are active
nnodes: ds4 NNODES: integer for total number of nodes in network
npipes: ds4 NPIPES: integer for total number of pipes in network
nlay: ds4 NLAYERS: integer for number of layers in model (defined in DIS package)
temp: ds6 TEMPERATURE: float for avg groundwater temp in conduits
sa_exch: ds14 SA_EXCHANGE: integer flag, 1=assign conduit wall permeability & let cfp comput pipe surface area
epsilon: ds16 EPSILON: float for convergence criterion (use a very small number)
niter: ds18 NITER: integer for max number of iterations allowed
relax: ds20 RELAX: step length for iterations (<1 may improve convergence)
p_nr: ds22 P_NR: integer print flag, if 1, print iteration results

File imports:

network_info_file: text file name string to import for ds8
       # NO_N, MC,MR,ML, NB1,NB2,NB3,NB4,NB5,NB6,PB1,PB2,PB3,PB4,PB5,PB6, 
       # node number, modflow col,row,lay, neighbor nodes (0 if none), connected pipes (0 if none)
geoheight_file: text file name to import for ds12
       # abs elevations of pipe nodes
pipe_info_file: text file name to import for ds25
       # NO_P,DIAMETER,TORTUOSITY,RHEIGHT,LCRITREY_P,TCRITREY_P, 
       # pipe num, diam, tortuosity, roughness height, lower critical Reynolds #, upper critical Reynolds #
node_head_file: text file name to import for ds27 
       # NO_N, N_HEAD: heads in nodes (if -1, calculated)
K_exch_file: text file name to import for ds29
       # NO_N, K_EXCHANGE: conduit wall permeability'''
    
    #Convert inputs to strings:
    [ds1,ds6,ds14,ds16,ds18,ds20,ds22] = [str(ds) for ds in [mode,temp,sa_exch,epsilon,niter,relax,p_nr]]
    ds4 = str(nnodes) + ' ' + str(npipes) + ' ' + str(nlay)

    #Import txt files as strings:
    with open (network_info_file, "r") as f:     
        ds8=f.read()
    with open (geoheight_file, "r") as f:     
        ds12=f.read()
    with open (pipe_info_file, "r") as f:     
        ds25=f.read()
    with open (node_head_file, "r") as f:      
        ds27=f.read()
    with open (K_exch_file, "r") as f:     
        ds29=f.read()

    #FORTRAN comment lines to include:
    ds0 = '# mode'                                                                    #ds0
    ds2 = '#data for mode 1 conduit pipe system'                                      #ds2
    ds3 = '#number of nodes / tubes / layers'                                         #ds3
    ds5 = '#temperature'                                                              #ds5
    ds7 = '#No mc mr ml Nb1 Nb2 Nb3 Nb4 Nb5 Nb6 tb1 tb2 tb3 tb4 tb5 tb6'              #ds7
    ds9 = '#elevation of conduit nodes. Two possibilities'                            #ds9
    ds10 = '#first: node # elevation (1 line for each node)'                          #ds10
    ds11 = '#second: nbrnodes elevaton (only one line used to assign constant value)' #ds11
    ds13 = '#surface dependent exchange (set 1) or constant exchange (set 0)'         #ds13
    ds15 = '#criterion for convergence'                                               #ds15
    ds17 = '#maximum number for loop iterations'                                      #ds17
    ds19 = '#parameter of relaxation'                                                 #ds19
    ds21 = '#newton raphson print flag'                                               #ds21
    ds23 = '#data for tube parameters'                                                #ds23
    ds24 = '#no. diameter tortuosity roughness lreynolds treynolds'                   #ds24
    ds26 = '#node heads (if head unequal -1 the head is fixed)'                       #ds26
    ds28 = '#exchange terms for flow between continuum and pipe-network'              #ds28

    cfp =[ds0,ds1,ds2,ds3,ds4,ds5,ds6,ds7,ds8,ds9,ds10,ds11,ds12,ds13,ds14,ds15,ds16,
          ds17,ds18,ds19,ds20,ds21,ds22,ds23,ds24,ds25,ds26,ds27,ds28,ds29]
    
    return cfp



#################################

def cfp_write_input(modelname, dataset_strings, filenames=['coc','crch','cfp']):
    
    '''Write CFP input files: Uses the coc, crch, and cfp dataset strings created by the preceding functions to write text files for MODFLOW

Inputs:

modelname: string for name of model (ex: 'test1')
filenames: list of strings for each file's desired name (ex: 'coc')
dataset_strings: list of strings created by the ModflowCoc etc. functions defined above'''
    
    for i in range(len(filenames)):                           #loop over files to create
        with open(modelname+'.'+str(filenames[i]), 'w') as f:     #create and open new text file for writing
            for ds in dataset_strings[i]:                 #loop over datasets to write
                write = f.write(ds+'\n')           #write each dataset and then go to a new line
            
            
###################################

def update_nam(modelname, coc_unit_num=16, crch_unit_num=18, cfp_unit_num=17):
    
    '''NAM: Update name file to include CFP input files. This will be appended to the existing FloPy-generated name file

Inputs:

modelname: string for model name
coc_unit_num: unit number to write COC to
crch_unit_num: unit number to write CRCH to
cfp_unit_num: unit number to write CFP to'''
    
    #create strings to add
    nam = ['COC' + '%17s'%coc_unit_num  + '  ' + modelname + '.coc'  + '\n',
        'CRCH'+ '%16s'%crch_unit_num + '  ' + modelname + '.crch' + '\n',
        'CFP' + '%17s'%cfp_unit_num  + '  ' + modelname + '.cfp']
    
    #write to existing name file
    with open(modelname+'.nam','a') as file:      #open existing name file for appending
        for cfp_package in nam:                   #loop over CFP package name strings
            write = file.write(cfp_package)       #write to the bottom of the name file
            
            
########################################################

def node_budget(modelname, node_num, ext='.list'):
    
    '''Get node budget info from LIST file. Reads in the list file, then finds & saves node budget data at each timestep for specified node. Returns a list of times and flows.

Inputs:

modelname: string for current model name
ext: string for file extensions of LIST file
node_num: desired node number to get budget for'''
    
    lines = []                                   #initialize empty list of line strings
    with open (modelname+ext, "r") as file:      #open list file for reading
        for line in file:                        #loop over each line
            lines.append(line)                   #add each line to the list of line strings

    node_bud_locs = []                           #initialize empty list of line numbers where budgets are
    t = []                                       #initialize empty list for time values
    Q = []                                       #initialize empty list for flow values
    for line_num,line in enumerate(lines):       #loop over each index,string pair for lines in list file
        if line.find('NODE WATER BUDGET')>-1:       #if this string is found in the current line
            node_bud_locs.append(line_num)                     #save line number
            t.append(float(lines[line_num+2][24:30]))          #save total time
            Q.append(float(lines[line_num+node_num+6][7:17]))  #save fixed head flow rate for desired node
    
    return [t,Q]                                 #return a list of times and flows


