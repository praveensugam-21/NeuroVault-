import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.services.ollama_service import OllamaService

context = (
    "Document: Aadhaar Card\n"
    "Type: Aadhaar Card\n"
    "Key Fields: name: Praveen Sugam, dob: 15/08/2001, address: 45 Nungambakkam High Road Chennai 600034\n\n"
    "Text Passages:\n"
    "Name: Praveen Sugam\n"
    "Date of Birth: 15/08/2001\n"
    "Gender: Male\n"
    "Address: 45 Nungambakkam High Road, Chennai, Tamil Nadu - 600034\n\n"
    "---\n\n"
    "Document: PAN Card\n"
    "Type: PAN Card\n"
    "Key Fields: name: Praveen Sugam, pan_number: ABCDE1234F\n\n"
    "Text Passages:\n"
    "Name: Praveen Sugam\n"
    "PAN Number: ABCDE1234F\n"
    "Father Name: Sugam Kumar"
)

question = "What is my name and address?"

prompt = (
    "You are IRIS, a secure AI document assistant.\n"
    "Answer ONLY using the document context below. Cite the document name.\n"
    "Use markdown formatting with bold labels.\n\n"
    "## Document Context:\n"
    + context +
    "\n\n## User Question:\n" + question +
    "\n\n## Answer:\n"
)


def run_checks():
    print("Sending to Ollama...")
    answer = OllamaService.generate_completion(prompt)
    print()
    print("=== IRIS RESPONSE ===")
    print(answer if answer else "ERROR: Empty response from Ollama")


if __name__ == "__main__":
    run_checks()
