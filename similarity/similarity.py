import numpy as np


def cosine_similarity(
    resume_embedding,
    jd_embedding
):

    resume = np.array(
        resume_embedding
    )

    jd = np.array(
        jd_embedding
    )

    similarity = np.dot(
        resume,
        jd
    ) / (
        np.linalg.norm(resume)
        * np.linalg.norm(jd)
    )

    return float(similarity)