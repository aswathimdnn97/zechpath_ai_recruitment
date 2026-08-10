from document_processing.resume.entity_extracter.certifications.certification_block_splitter import (
    split_certification_blocks,
)


def test_split_multiple_certifications_on_one_line():
    section = [
        "Microsoft Certified: Azure Developer Associate — Microsoft Certified: Azure AI Fundamentals — Google Cloud Professional Data Engineer — Machine Learning Specialization — TensorFlow Developer Certificate",
        "Microsoft",
        "Microsoft",
        "Google Cloud",
        "Coursera / Deep Learning.AI",
        "TensorFlow",
    ]

    blocks = split_certification_blocks(section)

    assert len(blocks) == 5
    assert blocks[0][0] == "Microsoft Certified: Azure Developer Associate"
    assert blocks[1][0] == "Microsoft Certified: Azure AI Fundamentals"
    assert blocks[2][0] == "Google Cloud Professional Data Engineer"
    assert blocks[3][0] == "Machine Learning Specialization"
    assert blocks[4][0] == "TensorFlow Developer Certificate"
