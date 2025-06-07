import pytest
from unittest.mock import Mock, patch
from translatron.translator import NonTranslator, AmazonTranslator

# Check if Google Cloud libraries are available
try:
    import google.cloud.translate_v2  # noqa: F401
    from translatron.translator import GoogleTranslator
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    GoogleTranslator = None


class TestNonTranslator:
    def setup_method(self):
        self.translator = NonTranslator()

    def test_detect_language(self):
        assert self.translator.detect_language("Hello") == "en"
        assert self.translator.detect_language("Hola") == "en"
        assert self.translator.detect_language("") == "en"

    def test_translate(self):
        assert self.translator.translate("Hello", "es") == "Hello"
        assert self.translator.translate("Hello", "fr") == "Hello"
        assert self.translator.translate("", "es") == ""
        assert self.translator.translate("Complex text", "zh") == "Complex text"

    def test_translate_with_detected_language(self):
        """Test that NonTranslator accepts detected_language parameter but ignores it."""
        assert self.translator.translate("Hello", "es", detected_language="en") == "Hello"
        assert self.translator.translate("Hello", "fr", detected_language="auto") == "Hello"
        assert self.translator.translate("Hello", "zh", detected_language=None) == "Hello"


class TestAmazonTranslator:
    def setup_method(self):
        with patch('boto3.client') as mock_boto_client:
            # Mock the clients
            self.mock_translate_client = Mock()
            self.mock_comprehend_client = Mock()

            def client_side_effect(service_name):
                if service_name == 'translate':
                    return self.mock_translate_client
                elif service_name == 'comprehend':
                    return self.mock_comprehend_client
                return Mock()

            mock_boto_client.side_effect = client_side_effect
            self.translator = AmazonTranslator()

    def test_detect_language(self):
        # Mock the comprehend response
        mock_response = {
            'Languages': [
                {
                    'LanguageCode': 'en',
                    'Score': 0.99
                }
            ]
        }

        self.mock_comprehend_client.detect_dominant_language.return_value = mock_response
        result = self.translator.detect_language("Hello world")
        assert result == "en"
        self.mock_comprehend_client.detect_dominant_language.assert_called_once_with(Text="Hello world")

    def test_detect_language_spanish(self):
        mock_response = {
            'Languages': [
                {
                    'LanguageCode': 'es',
                    'Score': 0.95
                }
            ]
        }
        
        self.mock_comprehend_client.detect_dominant_language.return_value = mock_response
        result = self.translator.detect_language("Hola mundo")
        assert result == "es"
        self.mock_comprehend_client.detect_dominant_language.assert_called_once_with(Text="Hola mundo")

    def test_translate_with_detected_language(self):
        mock_response = {
            'TranslatedText': 'Hola mundo',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'es'
        }

        self.mock_translate_client.translate_text.return_value = mock_response
        result = self.translator.translate("Hello world", "es", detected_language="en")
        assert result == "Hola mundo"

        # Verify the call was made with correct parameters
        self.mock_translate_client.translate_text.assert_called_with(
            Text="Hello world",
            SourceLanguageCode="en",
            TargetLanguageCode="es"
        )

    def test_translate_without_detected_language(self):
        mock_response = {
            'TranslatedText': 'Bonjour le monde',
            'SourceLanguageCode': 'auto',
            'TargetLanguageCode': 'fr'
        }

        self.mock_translate_client.translate_text.return_value = mock_response
        result = self.translator.translate("Hello world", "fr")
        assert result == "Bonjour le monde"

        # Verify the call was made with 'auto' as source language
        self.mock_translate_client.translate_text.assert_called_with(
            Text="Hello world",
            SourceLanguageCode="auto",
            TargetLanguageCode="fr"
        )

    def test_translate_empty_text(self):
        mock_response = {
            'TranslatedText': '',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'es'
        }

        self.mock_translate_client.translate_text.return_value = mock_response
        result = self.translator.translate("", "es", detected_language="en")
        assert result == ""

    def test_translate_client_error(self):
        self.mock_translate_client.translate_text.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
            self.translator.translate("Hello", "es")

    def test_detect_language_client_error(self):
        self.mock_comprehend_client.detect_dominant_language.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
            self.translator.detect_language("Hello")

    def test_translate_with_none_detected_language(self):
        """Test translate when detected_language is None (should use 'auto')."""
        mock_response = {
            'TranslatedText': 'Hola mundo',
            'SourceLanguageCode': 'auto',
            'TargetLanguageCode': 'es'
        }
        
        self.mock_translate_client.translate_text.return_value = mock_response
        result = self.translator.translate("Hello world", "es", detected_language=None)
        assert result == "Hola mundo"
        
        # Verify it defaults to 'auto' when detected_language is None
        self.mock_translate_client.translate_text.assert_called_with(
            Text="Hello world",
            SourceLanguageCode="auto",
            TargetLanguageCode="es"
        )


@pytest.mark.skipif(not GOOGLE_AVAILABLE, reason="Google Cloud libraries not available")
class TestGoogleTranslator:
    def setup_method(self):
        # Mock the Google Cloud translate client
        with patch('google.cloud.translate_v2.Client') as mock_client_class:
            self.mock_client = Mock()
            mock_client_class.return_value = self.mock_client
            self.translator = GoogleTranslator(credentials_path=None)

    def test_detect_language(self):
        # Mock the detect_language response
        mock_response = {
            'language': 'en',
            'confidence': 0.99
        }
        self.mock_client.detect_language.return_value = mock_response

        result = self.translator.detect_language("Hello world")
        assert result == "en"
        self.mock_client.detect_language.assert_called_once_with("Hello world")

    def test_detect_language_spanish(self):
        mock_response = {
            'language': 'es',
            'confidence': 0.95
        }
        self.mock_client.detect_language.return_value = mock_response

        result = self.translator.detect_language("Hola mundo")
        assert result == "es"

    def test_translate(self):
        mock_response = {
            'translatedText': 'Hola mundo',
            'detectedSourceLanguage': 'en'
        }
        self.mock_client.translate.return_value = mock_response

        result = self.translator.translate("Hello world", "es")
        assert result == "Hola mundo"
        self.mock_client.translate.assert_called_once_with("Hello world", target_language="es")

    def test_translate_with_detected_language(self):
        mock_response = {
            'translatedText': 'Hola mundo',
            'detectedSourceLanguage': 'en'
        }
        self.mock_client.translate.return_value = mock_response

        result = self.translator.translate("Hello world", "es", detected_language="en")
        assert result == "Hola mundo"
        self.mock_client.translate.assert_called_once_with("Hello world", target_language="es", source_language="en")

    def test_translate_with_auto_detected_language(self):
        """Test that 'auto' detected_language falls back to no source_language parameter."""
        mock_response = {
            'translatedText': 'Hola mundo',
            'detectedSourceLanguage': 'en'
        }
        self.mock_client.translate.return_value = mock_response

        result = self.translator.translate("Hello world", "es", detected_language="auto")
        assert result == "Hola mundo"
        self.mock_client.translate.assert_called_once_with("Hello world", target_language="es")

    def test_translate_with_none_detected_language(self):
        """Test that None detected_language falls back to no source_language parameter."""
        mock_response = {
            'translatedText': 'Hola mundo',
            'detectedSourceLanguage': 'en'
        }
        self.mock_client.translate.return_value = mock_response

        result = self.translator.translate("Hello world", "es", detected_language=None)
        assert result == "Hola mundo"
        self.mock_client.translate.assert_called_once_with("Hello world", target_language="es")

    def test_translate_french(self):
        mock_response = {
            'translatedText': 'Bonjour le monde',
            'detectedSourceLanguage': 'en'
        }
        self.mock_client.translate.return_value = mock_response

        result = self.translator.translate("Hello world", "fr")
        assert result == "Bonjour le monde"

    def test_translate_empty_text(self):
        mock_response = {
            'translatedText': '',
            'detectedSourceLanguage': 'en'
        }
        self.mock_client.translate.return_value = mock_response

        result = self.translator.translate("", "es")
        assert result == ""

    def test_translate_client_error(self):
        self.mock_client.translate.side_effect = Exception("Google API Error")

        with pytest.raises(Exception, match="Google API Error"):
            self.translator.translate("Hello", "es")

    def test_detect_language_client_error(self):
        self.mock_client.detect_language.side_effect = Exception("Google API Error")

        with pytest.raises(Exception, match="Google API Error"):
            self.translator.detect_language("Hello")

    def test_initialization_with_credentials_path(self):
        # Test that credentials_path parameter doesn't break initialization
        with patch('google.cloud.translate_v2.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            translator = GoogleTranslator(credentials_path="/path/to/creds.json")
            assert translator.client is not None

    def test_initialization_without_credentials_path(self):
        # Test that no credentials_path still works
        with patch('google.cloud.translate_v2.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            translator = GoogleTranslator(credentials_path=None)
            assert translator.client is not None


# Integration-style tests that verify the interface compliance
class TestTranslatorInterface:
    """Test that all translators implement the required interface correctly."""

    @pytest.fixture(params=[
        NonTranslator(),
        pytest.param(AmazonTranslator(), marks=pytest.mark.skipif(True, reason="Requires AWS credentials")),
    ])
    def translator(self, request):
        return request.param

    def test_detect_language_interface(self, translator):
        """Test that detect_language returns a string."""
        if isinstance(translator, NonTranslator):
            result = translator.detect_language("Hello")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_translate_interface(self, translator):
        """Test that translate returns a string."""
        if isinstance(translator, NonTranslator):
            result = translator.translate("Hello", "es")
            assert isinstance(result, str)

    def test_translate_with_detected_language_interface(self, translator):
        """Test that translate with detected_language parameter returns a string."""
        if isinstance(translator, NonTranslator):
            result = translator.translate("Hello", "es", detected_language="en")
            assert isinstance(result, str)
