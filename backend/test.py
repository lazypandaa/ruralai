from openai import AzureOpenAI

# ========================
# Configuration
# ========================
endpoint = "https://azadj-mh00wimr-eastus2.cognitiveservices.azure.com/"
deployment_name = "gpt35"  # Name of your deployed model
api_version = "2024-12-01-preview"
subscription_key = "CAeNSw3Kjc9b3CzNcyDOaNGCaStBqL9dmg1j9cU4RIVqNILKSMnVJQQJ99BJACHYHv6XJ3w3AAAAACOG6dVR"  # <-- Replace with your actual API key

# ========================
# Initialize client
# ========================
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version=api_version
)

# ========================
# Prepare messages
# ========================
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "I am going to Paris, what should I see?"}
]

# ========================
# Make API call
# ========================
try:
    response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0
    )

    # Print the assistant's reply
    print("Assistant response:")
    print(response.choices[0].message.content)

except Exception as e:
    print("Error calling Azure OpenAI API:", str(e))

