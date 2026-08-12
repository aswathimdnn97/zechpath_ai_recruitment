from  embeddings.embedding_generator import EmbeddingGenerator
from similarity.similarity import cosine_similarity
from embeddings.section_embedding import generate_section_embeddings
from similarity.section_similarity import calculate_section_similarities


def generate_matching_result(candidate, job):

    # --------------------------------
    # 1. Full Resume/JD Embeddings
    # --------------------------------

    generator = EmbeddingGenerator()

    resume_embedding = generator.generate_candidate_embedding(
        candidate
    )

    jd_embedding = generator.generate_jd_embedding(
        job
    )

    # --------------------------------
    # 2. Overall Similarity
    # --------------------------------

    overall_similarity = cosine_similarity(
        resume_embedding,
        jd_embedding
    )

    # --------------------------------
    # 3. Section Embeddings
    # --------------------------------

    section_embeddings = generate_section_embeddings(
        candidate,
        job
    )

    # --------------------------------
    # 4. Section Similarities
    # --------------------------------

    section_scores = calculate_section_similarities(
        section_embeddings["resume"],
        section_embeddings["jd"]
    )

    # --------------------------------
    # 5. Return Result
    # --------------------------------

    return {
        "overall_similarity": overall_similarity,
        "section_similarity": section_scores
    }