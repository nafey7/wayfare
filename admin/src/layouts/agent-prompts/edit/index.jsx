import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

// Material Dashboard 2 React components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import MDInput from "components/MDInput";
import MDAlert from "components/MDAlert";

// Material Dashboard 2 React example components
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";

// Material UI
import { Card, Grid, TextareaAutosize, FormControlLabel, Switch } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SaveIcon from "@mui/icons-material/Save";

// API
import agentPromptsApi from "../../../api/agentPrompts/agentPromptsApi";

function EditAgentPrompt() {
  const { agentName } = useParams();
  const navigate = useNavigate();
  
  const [prompt, setPrompt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const [formData, setFormData] = useState({
    goal: "",
    prompt_template: "",
    is_active: true
  });

  useEffect(() => {
    fetchPrompt();
  }, [agentName]);

  const fetchPrompt = async () => {
    try {
      setLoading(true);
      const response = await agentPromptsApi.getPromptByAgent(agentName);
      setPrompt(response);
      setFormData({
        goal: response.goal || "",
        prompt_template: response.prompt_template || "",
        is_active: response.is_active ?? true
      });
      setError(null);
    } catch (err) {
      console.error("Error fetching prompt:", err);
      if (err.response?.status === 404) {
        setError(`No prompt found for agent: ${agentName}. You can create a new one by filling out the form below.`);
      } else {
        setError("Failed to load agent prompt");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    if (!formData.goal.trim() || !formData.prompt_template.trim()) {
      setError("Both goal and prompt template are required");
      return;
    }

    try {
      setSaving(true);
      
      if (prompt) {
        // Update existing prompt
        await agentPromptsApi.updatePrompt(agentName, formData);
        setSuccess("Agent prompt updated successfully");
      } else {
        // Create new prompt
        const createData = {
          agent_name: agentName,
          ...formData
        };
        await agentPromptsApi.createPrompt(createData);
        setSuccess("Agent prompt created successfully");
      }
      
      setError(null);
      
      // Refresh prompt data
      await fetchPrompt();
      
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      console.error("Error saving prompt:", err);
      setError(err.response?.data?.detail || "Failed to save agent prompt");
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    navigate("/admin/agent-prompts");
  };

  const formatAgentName = (name) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getAgentDescription = (name) => {
    const descriptions = {
      "intent_recognizer": "Classifies user messages into predefined intents (BOOK_FLIGHT, VIEW_BOOKINGS, etc.) using Gemini AI with pattern-matching fallback",
      "data_extractor": "Extracts structured flight booking data (origin, destination, dates, passengers) from natural language messages using Gemini AI with validation",
      "general_travel_handler": "Generates conversational AI responses for non-flight travel queries using the 'MyVoya' personality via Gemini AI"
    };
    return descriptions[name] || "AI agent for processing user interactions";
  };

  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox py={3}>
        <MDBox mb={3}>
          <Card>
            <MDBox
              mx={2}
              mt={-3}
              py={3}
              px={2}
              variant="gradient"
              bgColor="info"
              borderRadius="lg"
              coloredShadow="info"
              display="flex"
              justifyContent="space-between"
              alignItems="center"
            >
              <MDBox display="flex" alignItems="center">
                <MDButton
                  variant="outlined"
                  color="white"
                  size="small"
                  startIcon={<ArrowBackIcon />}
                  onClick={handleBack}
                  sx={{ mr: 2 }}
                >
                  Back
                </MDButton>
                <MDTypography variant="h6" color="white">
                  Edit Agent Prompt: {formatAgentName(agentName)}
                </MDTypography>
              </MDBox>
              <MDButton
                variant="contained"
                color="white"
                size="small"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Changes"}
              </MDButton>
            </MDBox>

            <MDBox p={3}>
              {error && (
                <MDAlert color="error" dismissible>
                  {error}
                </MDAlert>
              )}
              
              {success && (
                <MDAlert color="success" dismissible>
                  {success}
                </MDAlert>
              )}

              {loading ? (
                <MDBox display="flex" justifyContent="center" p={3}>
                  <MDTypography variant="body2" color="text">
                    Loading agent prompt...
                  </MDTypography>
                </MDBox>
              ) : (
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <MDBox mb={2}>
                      <MDTypography variant="h6" gutterBottom>
                        Agent Information
                      </MDTypography>
                      <MDTypography variant="body2" color="text">
                        <strong>Purpose:</strong> {getAgentDescription(agentName)}
                      </MDTypography>
                    </MDBox>
                  </Grid>

                  <Grid item xs={12}>
                    <MDBox mb={2}>
                      <MDTypography variant="body2" fontWeight="medium" mb={1}>
                        Goal Description
                      </MDTypography>
                      <MDInput
                        fullWidth
                        multiline
                        rows={3}
                        value={formData.goal}
                        onChange={(e) => handleInputChange('goal', e.target.value)}
                        placeholder="Describe what this agent does and its purpose..."
                      />
                    </MDBox>
                  </Grid>

                  <Grid item xs={12}>
                    <MDBox mb={2}>
                      <MDTypography variant="body2" fontWeight="medium" mb={1}>
                        Prompt Template
                      </MDTypography>
                      <MDTypography variant="caption" color="text" mb={1} display="block">
                        This is the prompt sent to the AI model. Use placeholders like {"{message}"}, {"{context}"}, etc.
                      </MDTypography>
                      <TextareaAutosize
                        minRows={15}
                        style={{
                          width: '100%',
                          padding: '12px',
                          border: '1px solid #d2d6da',
                          borderRadius: '8px',
                          fontFamily: 'monospace',
                          fontSize: '14px',
                          resize: 'vertical'
                        }}
                        value={formData.prompt_template}
                        onChange={(e) => handleInputChange('prompt_template', e.target.value)}
                        placeholder="Enter the prompt template for this agent..."
                      />
                    </MDBox>
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={formData.is_active}
                          onChange={(e) => handleInputChange('is_active', e.target.checked)}
                          color="info"
                        />
                      }
                      label={
                        <MDTypography variant="body2">
                          Active (prompt is currently in use)
                        </MDTypography>
                      }
                    />
                  </Grid>

                  {prompt && (
                    <Grid item xs={12}>
                      <MDBox mt={2} p={2} bgcolor="grey.100" borderRadius={1}>
                        <MDTypography variant="caption" color="text">
                          <strong>Created:</strong> {new Date(prompt.created_at).toLocaleString()}
                          <br />
                          <strong>Last Updated:</strong> {new Date(prompt.updated_at).toLocaleString()}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                  )}
                </Grid>
              )}
            </MDBox>
          </Card>
        </MDBox>
      </MDBox>
    </DashboardLayout>
  );
}

export default EditAgentPrompt;