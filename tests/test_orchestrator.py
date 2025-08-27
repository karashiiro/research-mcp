"""
Unit tests for ResearchOrchestrator.

Tests the core research orchestration functionality including workflow delegation,
response processing, source tracking, and error handling.
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from research_orchestrator.orchestrator import (
    ResearchOrchestrator,
    extract_content_text,
)
from research_orchestrator.processing import (
    CitationProcessor,
    ResultFormatter,
    SourceTracker,
)


class TestExtractContentText:
    """Test cases for the extract_content_text utility function."""

    def test_extract_simple_text_content(self):
        """Test extracting text from simple text content block."""
        content_block = {"text": "Simple text content"}
        result = extract_content_text(content_block)
        assert result == "Simple text content"

    def test_extract_reasoning_content(self):
        """Test extracting text from reasoning content format."""
        content_block = {
            "reasoningContent": {"reasoningText": {"text": "Reasoning text content"}}
        }
        result = extract_content_text(content_block)
        assert result == "Reasoning text content"

    def test_extract_empty_content(self):
        """Test extracting from empty content block."""
        content_block = {}
        result = extract_content_text(content_block)
        assert result == ""

    def test_extract_invalid_reasoning_content(self):
        """Test extracting from malformed reasoning content."""
        content_block = {"reasoningContent": {"invalid": "structure"}}
        result = extract_content_text(content_block)
        assert result == ""


class TestResearchOrchestrator:
    """Test cases for ResearchOrchestrator functionality."""

    @pytest.fixture
    def mock_cache(self):
        """Mock SearchCache instance."""
        cache = Mock()
        return cache

    @pytest.fixture
    def mock_web_fetcher(self):
        """Mock WebContentFetcher instance."""
        web_fetcher = Mock()
        return web_fetcher

    @pytest.fixture
    def mock_model(self):
        """Mock model instance."""
        model = Mock()
        model.model_id = "test-model"
        return model

    @pytest.fixture
    def mock_agent_manager(self):
        """Mock AgentManager instance."""
        agent_manager = Mock()
        agent_manager.last_research_sources = [
            "https://example.com/source1",
            "https://example.com/source2",
        ]

        # Mock lead researcher
        lead_researcher = Mock()
        lead_researcher.return_value = Mock(
            message={
                "content": [
                    {
                        "text": '## Research Report\n\nThis is a test synthesis [1][2].\n\n## Sources\n\n[1] Test Source – "Title" – https://example.com/source1\n[2] Another Source – "Title" – https://example.com/source2'
                    }
                ]
            }
        )
        agent_manager.get_lead_researcher.return_value = lead_researcher
        return agent_manager

    @pytest.fixture
    def mock_logger(self):
        """Mock research logger."""
        logger = Mock()
        return logger

    @pytest.fixture
    def orchestrator(self, mock_cache, mock_web_fetcher):
        """Create ResearchOrchestrator instance with mocked dependencies."""
        with (
            patch(
                "research_orchestrator.orchestrator.create_model"
            ) as mock_create_model,
            patch(
                "research_orchestrator.orchestrator.create_agent_manager"
            ) as mock_create_agent_manager,
            patch(
                "research_orchestrator.orchestrator.setup_logging"
            ) as mock_setup_logging,
        ):
            mock_model = Mock()
            mock_create_model.return_value = mock_model

            mock_agent_manager = Mock()
            mock_agent_manager.last_research_sources = []
            mock_create_agent_manager.return_value = mock_agent_manager

            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger

            orchestrator = ResearchOrchestrator(
                progress_callback=None, cache=mock_cache, web_fetcher=mock_web_fetcher
            )

            return orchestrator

    def test_orchestrator_initialization(self, mock_cache, mock_web_fetcher):
        """Test ResearchOrchestrator initialization with all components."""
        with (
            patch(
                "research_orchestrator.orchestrator.create_model"
            ) as mock_create_model,
            patch(
                "research_orchestrator.orchestrator.create_agent_manager"
            ) as mock_create_agent_manager,
            patch(
                "research_orchestrator.orchestrator.setup_logging"
            ) as mock_setup_logging,
        ):
            mock_model = Mock()
            mock_create_model.return_value = mock_model

            mock_agent_manager = Mock()
            mock_create_agent_manager.return_value = mock_agent_manager

            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger

            progress_callback = Mock()
            orchestrator = ResearchOrchestrator(
                progress_callback=progress_callback,
                cache=mock_cache,
                web_fetcher=mock_web_fetcher,
            )

            # Verify model creation
            mock_create_model.assert_called_once()

            # Verify agent manager creation with correct parameters
            mock_create_agent_manager.assert_called_once_with(
                mock_model,
                progress_callback,
                cache=mock_cache,
                web_fetcher=mock_web_fetcher,
            )

            # Verify logging setup
            mock_setup_logging.assert_called_once()

            # Verify processing components initialization
            assert isinstance(orchestrator.citation_processor, CitationProcessor)
            assert isinstance(orchestrator.result_formatter, ResultFormatter)
            assert isinstance(orchestrator.source_tracker, SourceTracker)

            # Verify attributes
            assert orchestrator.model == mock_model
            assert orchestrator.agent_manager == mock_agent_manager
            assert orchestrator.research_logger == mock_logger
            assert orchestrator.progress_callback == progress_callback

    def test_orchestrator_initialization_no_callback(
        self, mock_cache, mock_web_fetcher
    ):
        """Test ResearchOrchestrator initialization without progress callback."""
        with (
            patch("research_orchestrator.orchestrator.create_model"),
            patch("research_orchestrator.orchestrator.create_agent_manager"),
            patch("research_orchestrator.orchestrator.setup_logging"),
        ):
            orchestrator = ResearchOrchestrator(
                cache=mock_cache, web_fetcher=mock_web_fetcher
            )

            assert orchestrator.progress_callback is None

    @pytest.mark.asyncio
    async def test_complete_research_workflow_success(self, orchestrator):
        """Test successful completion of research workflow."""
        main_topic = "Artificial Intelligence in Healthcare"

        # Mock lead researcher response
        mock_response = Mock(
            message={
                "content": [
                    {
                        "text": '# AI in Healthcare Report\n\nAI is transforming healthcare [1].\n\n## Sources\n\n[1] Medical AI – "Healthcare AI" – https://example.com/ai-healthcare'
                    }
                ]
            }
        )

        mock_lead_researcher = Mock(return_value=mock_response)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = [
            "https://example.com/ai-healthcare"
        ]

        result = await orchestrator.complete_research_workflow(main_topic)

        # Verify lead researcher was called with correct prompt
        mock_lead_researcher.assert_called_once()
        call_args = mock_lead_researcher.call_args[0][0]
        assert (
            f'conduct a complete research workflow for the topic: "{main_topic}"'
            in call_args
        )
        assert "COMPLETE WORKFLOW:" in call_args
        assert "CITATION REVIEW WORKFLOW:" in call_args

        # Verify result structure
        assert isinstance(result, dict)  # ResearchResults TypedDict
        assert result["main_topic"] == main_topic
        assert "AI is transforming healthcare" in result["master_synthesis"]
        assert "via delegation to lead researcher" in result["summary"]
        assert result["total_unique_sources"] >= 1
        assert len(result["all_sources_used"]) >= 1

        # Verify logging calls
        orchestrator.research_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_complete_research_workflow_with_source_processing(
        self, orchestrator
    ):
        """Test research workflow with proper source tracking and processing."""
        main_topic = "Machine Learning"

        # Mock lead researcher response with multiple sources
        mock_response = Mock(
            message={
                "content": [
                    {
                        "text": '# ML Report\n\nML algorithms [1] and neural networks [2].\n\n## Sources\n\n[1] ML Guide – "Algorithms" – https://example.com/ml\n[2] Neural Networks – "Guide" – https://example.com/nn'
                    }
                ]
            }
        )

        mock_lead_researcher = Mock(return_value=mock_response)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = [
            "https://example.com/ml",
            "https://example.com/nn",
            "https://example.com/additional",
        ]

        result = await orchestrator.complete_research_workflow(main_topic)

        # Verify source tracking
        assert result["total_unique_sources"] == 3
        assert "https://example.com/ml" in result["all_sources_used"]
        assert "https://example.com/nn" in result["all_sources_used"]
        assert "https://example.com/additional" in result["all_sources_used"]

        # Verify additional sources section was added
        assert "Additional Research Sources" in result["master_synthesis"]

    @pytest.mark.asyncio
    async def test_complete_research_workflow_error_handling(self, orchestrator):
        """Test error handling in research workflow."""
        main_topic = "Test Topic"

        # Mock lead researcher to raise an exception
        mock_lead_researcher = Mock(side_effect=Exception("Research failed"))
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )

        with pytest.raises(
            RuntimeError, match="Research workflow failed for topic 'Test Topic'"
        ):
            await orchestrator.complete_research_workflow(main_topic)

        # Verify error logging
        orchestrator.research_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_complete_research_workflow_timing_and_logging(self, orchestrator):
        """Test that workflow properly logs timing information."""
        main_topic = "Test Topic"

        # Mock lead researcher with delay to test timing
        def slow_research(prompt):
            time.sleep(0.01)  # Small delay for testing
            return Mock(message={"content": [{"text": "Test result"}]})

        mock_lead_researcher = Mock(side_effect=slow_research)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = []

        await orchestrator.complete_research_workflow(main_topic)

        # Verify logging calls include timing information
        log_calls = [
            call[0][0] for call in orchestrator.research_logger.info.call_args_list
        ]

        # Check for workflow start
        assert any("Starting complete research workflow" in call for call in log_calls)

        # Check for delegation timing
        assert any("Lead researcher completed in" in call for call in log_calls)

        # Check for processing timing
        assert any("Response processing completed in" in call for call in log_calls)

        # Check for total workflow timing
        assert any("Complete research workflow finished" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_complete_research_workflow_content_extraction(self, orchestrator):
        """Test proper extraction of content from different content block formats."""
        main_topic = "Content Test"

        # Mock response with mixed content formats
        mock_response = Mock(
            message={
                "content": [
                    {"text": "Part 1 "},
                    {"reasoningContent": {"reasoningText": {"text": "Part 2 "}}},
                    {"text": "Part 3"},
                    {},  # Empty content block
                ]
            }
        )

        mock_lead_researcher = Mock(return_value=mock_response)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = []

        result = await orchestrator.complete_research_workflow(main_topic)

        # Verify content was properly extracted and concatenated
        assert "Part 1 Part 2 Part 3" in result["master_synthesis"]

    @pytest.mark.asyncio
    async def test_conduct_research(self, orchestrator):
        """Test the main conduct_research method."""
        main_topic = "AI Research"

        # Mock the complete_research_workflow method
        expected_result = {
            "main_topic": main_topic,
            "subtopics_count": 0,
            "subtopic_research": [],
            "master_synthesis": "Test synthesis",
            "summary": "Test summary",
            "generated_at": "2024-01-01T00:00:00",
            "total_unique_sources": 1,
            "all_sources_used": ["https://example.com/test"],
        }

        orchestrator.complete_research_workflow = AsyncMock(
            return_value=expected_result
        )

        result = await orchestrator.conduct_research(main_topic)

        # Verify workflow was called
        orchestrator.complete_research_workflow.assert_called_once_with(main_topic)

        # Verify result
        assert result == expected_result

        # Verify logging
        log_calls = [
            call[0][0] for call in orchestrator.research_logger.info.call_args_list
        ]
        assert any("Starting research orchestration" in call for call in log_calls)
        assert any(
            "stable architecture with hybrid model pool" in call for call in log_calls
        )
        assert any("Research workflow completed" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_workflow_uuid_generation(self, orchestrator):
        """Test that each workflow gets a unique ID for tracking."""
        main_topic = "UUID Test"

        mock_response = Mock(message={"content": [{"text": "Test"}]})
        mock_lead_researcher = Mock(return_value=mock_response)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = []

        # Run workflow twice
        await orchestrator.complete_research_workflow(main_topic)
        await orchestrator.complete_research_workflow(main_topic)

        # Verify that different UUIDs were used in logging
        log_calls = [
            call[0][0] for call in orchestrator.research_logger.info.call_args_list
        ]
        workflow_logs = [
            call for call in log_calls if "Starting complete research workflow" in call
        ]

        assert len(workflow_logs) == 2
        # UUIDs should be different, so log messages should be different
        assert workflow_logs[0] != workflow_logs[1]

    def test_processing_components_integration(self, orchestrator):
        """Test that processing components are properly integrated."""
        # Verify components are properly initialized
        assert orchestrator.citation_processor is not None
        assert orchestrator.result_formatter is not None
        assert orchestrator.source_tracker is not None

        # Verify they are the correct types
        assert isinstance(orchestrator.citation_processor, CitationProcessor)
        assert isinstance(orchestrator.result_formatter, ResultFormatter)
        assert isinstance(orchestrator.source_tracker, SourceTracker)

    @pytest.mark.asyncio
    async def test_error_propagation_with_context(self, orchestrator):
        """Test that errors are properly wrapped with context."""
        main_topic = "Error Test"

        original_error = ValueError("Original error message")
        mock_lead_researcher = Mock(side_effect=original_error)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )

        with pytest.raises(RuntimeError) as exc_info:
            await orchestrator.complete_research_workflow(main_topic)

        # Verify error message includes topic context
        assert "Research workflow failed for topic 'Error Test'" in str(exc_info.value)

        # Verify original exception is preserved as cause
        assert exc_info.value.__cause__ == original_error

    @pytest.mark.asyncio
    async def test_workflow_with_empty_sources(self, orchestrator):
        """Test workflow handling when no sources are available."""
        main_topic = "Empty Sources Test"

        mock_response = Mock(message={"content": [{"text": "Report without sources"}]})
        mock_lead_researcher = Mock(return_value=mock_response)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = []  # No sources

        result = await orchestrator.complete_research_workflow(main_topic)

        # Should still work with empty sources
        assert result["main_topic"] == main_topic
        assert result["total_unique_sources"] == 0
        assert result["all_sources_used"] == []
        assert "Report without sources" in result["master_synthesis"]

    @pytest.mark.asyncio
    async def test_workflow_prompt_structure(self, orchestrator):
        """Test that the workflow prompt contains all required sections."""
        main_topic = "Prompt Test"

        mock_response = Mock(message={"content": [{"text": "Test"}]})
        mock_lead_researcher = Mock(return_value=mock_response)
        orchestrator.agent_manager.get_lead_researcher.return_value = (
            mock_lead_researcher
        )
        orchestrator.agent_manager.last_research_sources = []

        await orchestrator.complete_research_workflow(main_topic)

        # Get the prompt that was sent to the lead researcher
        prompt = mock_lead_researcher.call_args[0][0]

        # Verify all required sections are present
        assert "COMPLETE WORKFLOW:" in prompt
        assert "1. Generate 2-5 focused subtopics" in prompt
        assert "2. Use research_specialist tool" in prompt
        assert "3. Review initial findings" in prompt
        assert "4. Consider using research_specialist tool again" in prompt
        assert "5. Create a comprehensive master synthesis" in prompt
        assert "FOLLOW-UP RESEARCH CONSIDERATIONS:" in prompt
        assert (
            "CRITICAL: Your final synthesis report MUST include proper citations"
            in prompt
        )
        assert "CITATION REVIEW WORKFLOW:" in prompt
        assert "Return ONLY the final master synthesis report" in prompt

        # Verify topic is properly embedded
        assert (
            f'conduct a complete research workflow for the topic: "{main_topic}"'
            in prompt
        )
