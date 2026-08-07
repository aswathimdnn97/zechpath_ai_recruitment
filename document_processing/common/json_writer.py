import json
import os

def save_resume(text,file_name):
    
    # create a folder to save structured resume
    os.makedirs("data/extracted",exist_ok=True)
    
    # store data in dictionary
    resume_data={
        "resume_text":text
    }
    
    # full filepath
    file_path=os.path.join("data","extracted",file_name+".json")
    
    #save Json resume
    with open(file_path,"w",encoding="utf-8") as file:
        json.dump(resume_data,file,indent=4)
        
    print(f"Extracted Resume Saved")
    