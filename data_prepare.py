import sklearn.model_selection as ms
import numpy as np
import scipy.io as sio
import math
import torch
# Author: Haoming Zhang
#The code here not only include data importing, but also data standardization and the generation of analog noise signals

def get_rms(records):
   
    return math.sqrt(sum([x ** 2 for x in records]) / len(records))


def random_signal(signal,combin_num):
    # Random disturb and augment signal
    random_result=[]

    for i in range(combin_num):
        random_num = np.random.permutation(signal.shape[0])
        shuffled_dataset = signal[random_num, :]
        shuffled_dataset = shuffled_dataset.reshape(signal.shape[0],signal.shape[1])
        random_result.append(shuffled_dataset)
    
    random_result  = np.array(random_result)

    return  random_result

def prepare_data(DEVICE,batch_size,EEG_all, noise_all, combin_num, train_num, noise_type):
    # Here we use eeg and noise signal to generate scale transed training, validation, test signal
    print(EEG_all.shape) # 4514 512
    print(noise_all.shape) # 3400 512
    EEG_all_random = np.squeeze(random_signal(signal = EEG_all, combin_num = 1))
    noise_all_random = np.squeeze(random_signal(signal = noise_all, combin_num = 1))  
    
    if noise_type == 'EMG':  # Training set will Reuse some of the EEG signal to much the number of EMG
        reuse_num = noise_all_random.shape[0] - EEG_all_random.shape[0]
        EEG_reuse = EEG_all_random[0 : reuse_num, :]
        EEG_all_random = np.vstack([EEG_reuse, EEG_all_random])
        print('EEG segments after reuse: ',EEG_all_random.shape[0])

    elif noise_type == 'EOG':  # We will drop some of the EEG signal to much the number of EMG
        EEG_all_random = EEG_all_random[0:noise_all_random.shape[0]]
        print('EEG segments after drop: ',EEG_all_random.shape[0])

#------------------to divided------------------------
    # get the 
    timepoint = noise_all_random.shape[1]
#     train_num = round(train_per * EEG_all_random.shape[0]) # the number of segmentations used in training process
    
#     validation_num = round((EEG_all_random.shape[0] - train_num) / 2) # the number of segmentations used in validation process
    
    #test_num = EEG_all_random.shape[0] - train_num - validation_num  # Rest are the number of segmentations used in test process

    #take train data    
    train_eeg = EEG_all_random[0 : train_num, :]
#     validation_eeg = EEG_all_random[train_num : train_num + validation_num, :]

    #train3000，test400
    test_eeg = EEG_all_random[train_num  : EEG_all_random.shape[0], :]

    train_noise = noise_all_random[0 : train_num, :]
#     validation_noise = noise_all_random[train_num : train_num + validation_num,:]
    test_noise = noise_all_random[train_num : noise_all_random.shape[0], :]

    EEG_train = random_signal(signal = train_eeg, combin_num = combin_num).reshape(combin_num * train_eeg.shape[0], timepoint)
    NOISE_train = random_signal(signal = train_noise, combin_num = combin_num).reshape(combin_num * train_noise.shape[0], timepoint)

    print('EEG_train.shape:',EEG_train.shape)
    print('noiseEEG_train.shape:',NOISE_train.shape)
    
    #################################  simulate noise signal of training set  ##############################

    #create random number between -10dB ~ 2dB
    # SNR_train_dB = np.random.uniform(-7, 2, (1))
    SNR_train_dB=[2]
    SNR_train_dB=np.array(SNR_train_dB)
    SNR_train = 10 ** (0.1 * (SNR_train_dB))

    # combin eeg and noise for training set by plus
    noiseEEG_train=[]
    noiseEEG_train_T=[]
    for i in range (EEG_train.shape[0]):
        eeg=EEG_train[i].reshape(EEG_train.shape[1])
        noise=NOISE_train[i].reshape(NOISE_train.shape[1])

        #add NOISE
        coe=get_rms(eeg)/(get_rms(noise)*SNR_train[0])
        noise = noise*coe
        neeg = noise+eeg
        noiseEEG_train.append(neeg)
        #substract NOISE to create target EEG_noise
        coe=get_rms(eeg)/(get_rms(noise)*SNR_train[0])
        noise = noise*coe
        neeg = noise-eeg
        noiseEEG_train_T.append(neeg)
    

    noiseEEG_train=np.array(noiseEEG_train)
    noiseEEG_train_Target=np.array(noiseEEG_train_T)

    # variance for noisy EEG
    noiseEEG_train_end_standard = []
    noiseEEG_train_Target_end_standard=[]
    for i in range(noiseEEG_train.shape[0]):
        # Each epochs divided by the standard deviation
        noiseeeg_train_Target_end_standard = noiseEEG_train_Target[i] / np.std(noiseEEG_train_Target[i])
        noiseEEG_train_Target_end_standard.append(noiseeeg_train_Target_end_standard)

        noiseeeg_train_end_standard = noiseEEG_train[i] / np.std(noiseEEG_train[i])
        noiseEEG_train_end_standard.append(noiseeeg_train_end_standard)

    noiseEEG_train_Target_end_standard = np.array(noiseEEG_train_Target_end_standard)
    noiseEEG_train_end_standard = np.array(noiseEEG_train_end_standard)

    print('training data prepared', noiseEEG_train_end_standard.shape, noiseEEG_train_Target_end_standard.shape )

    #################################  simulate noise signal of test  ##############################

    # SNR_test_dB = np.linspace(-7.0, 2.0, num=(1))
    SNR_test_dB=[2]
    SNR_test_dB=np.array(SNR_test_dB)
    SNR_test = 10 ** (0.1 * (SNR_test_dB))

    eeg_test = np.array(test_eeg)
    noise_test = np.array(test_noise)
    
    # combin eeg and noise for test set 
    EEG_test = []
    noise_EEG_test = []
    noise_EEG_Targe_test = []
    
    #pick a SNR
    for i in range(1):
        
        noise_eeg_test = []
        noise_eeg_Target_test = []
        
        for j in range(eeg_test.shape[0]):
            eeg = eeg_test[j]
            noise = noise_test[j]
            
            coe = get_rms(eeg) / (get_rms(noise) * SNR_test[i])
            noise = noise * coe
            neeg = noise + eeg
            
            noise_eeg_test.append(neeg)
            #Target EEG_noise
            eeg = eeg_test[j]
            noise = noise_test[j]
            
            coe = get_rms(eeg) / (get_rms(noise) * SNR_test[i])
            noise = noise * coe
            neeg = noise - eeg
            
            noise_eeg_Target_test.append(neeg)        
        EEG_test.extend(eeg_test)
        
        noise_EEG_Targe_test.extend(noise_eeg_Target_test)        
        noise_EEG_test.extend(noise_eeg_test)


    noise_EEG_test = np.array(noise_EEG_test)
    noise_EEG_Targe_test = np.array(noise_EEG_Targe_test)
    EEG_test = np.array(EEG_test)


    # std for noisy EEG
    EEG_test_end_standard = []

    noiseEEG_test_end_standard = []
    noiseEEG_test_Target_end_standard = []

    std_VALUE = []
    std_VALUE_Target = []
    for i in range(noise_EEG_test.shape[0]):
        #-----------------
        # store std value to restore EEG signal
        std_value = np.std(noise_EEG_test[i])
        std_VALUE.append(std_value)

        std_value_Target = np.std(noise_EEG_Targe_test[i])
        std_VALUE_Target.append(std_value_Target)

#-------------------------

        # Each epochs of eeg and neeg was divide by the standard deviation
        eeg_test_all_std = EEG_test[i] / std_value
        EEG_test_end_standard.append(eeg_test_all_std)

        # eeg_test_all_std_Target = EEG_test[i] / std_value_Target
        # EEG_test_end_standard.append(eeg_test_all_std_Target)

        noiseeeg_test_end_standard = noise_EEG_test[i] / std_value
        noiseEEG_test_end_standard.append(noiseeeg_test_end_standard)

        noiseeeg_test_Target_end_standard = noise_EEG_Targe_test[i] / std_value_Target
        noiseEEG_test_Target_end_standard.append(noiseeeg_test_Target_end_standard)

    std_VALUE = np.array(std_VALUE)
    noiseEEG_test_end_standard = np.array(noiseEEG_test_end_standard)
    noiseEEG_test_Target_end_standard = np.array(noiseEEG_test_Target_end_standard)

    print('test data prepared, test data shape: ', noiseEEG_test_end_standard.shape,noiseEEG_test_Target_end_standard.shape)

    #--input data
    # train_x = torch.from_numpy(noiseEEG_train_end_standard).type(torch.FloatTensor)#.to(DEVICE)  # (B, N, F, T)
    # train_target = torch.from_numpy(EEG_train_end_standard).type(torch.FloatTensor)#.to(DEVICE)  # (B, N, T)
    # train_dataset = torch.utils.data.TensorDataset(train_x, train_target)
    # train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=False)

    # test_x = torch.from_numpy(noiseEEG_test_end_standard).type(torch.FloatTensor)#.to(DEVICE)  # (B, N, F, T)
    # test_target = torch.from_numpy(EEG_test_end_standard).type(torch.FloatTensor)#.to(DEVICE)  # (B, N, T)
    # test_dataset = torch.utils.data.TensorDataset(test_x, test_target)
    # test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    # return train_loader, test_loader 

    return noiseEEG_train_end_standard, noiseEEG_train_Target_end_standard, noiseEEG_test_end_standard, noiseEEG_test_Target_end_standard, std_VALUE
  
