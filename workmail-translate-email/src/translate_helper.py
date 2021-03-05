import boto3

comprehend = boto3.client(service_name='comprehend')
translate = boto3.client(service_name='translate')

def detect_language(text):
    """
    Detects the dominant language in a text
    Parameters
    ----------
    text: string, required
        Input text
    Returns
    -------
    string
        Representing language code of the dominant language
    """
    # Sending call to get language
    result = comprehend.detect_dominant_language(Text = text)['Languages']
    # Since the result can contain more than one language find the one with the highest score.
    high_score = 0
    best_guess = ''
    for lang in range(len(result)):
        if result[lang]['Score'] > high_score:
            high_score = result[lang]['Score']
            best_guess = result[lang]['LanguageCode']

    return best_guess

def translate_text(text, source_lang, destination_lang):
    """
    Translates given text from source language into destination language
    Parameters
    ----------
    text: string, required
        Input text in source language
    Returns
    -------
    string
        Translated text in destination language
    """
    result = translate.translate_text(Text=text,
            SourceLanguageCode=source_lang, TargetLanguageCode=destination_lang)
    return result.get('TranslatedText')
