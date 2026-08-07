from  document_processing.common.json_writer import save_resume

def test_json_resume():
    file="data/resume/pdf/jsmpwkcwyntg.pdf"
    save_resume(file,"resume2")