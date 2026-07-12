import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

// Material Dashboard 2 React components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import MDAlert from "components/MDAlert";

// Material Dashboard 2 React example components
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";

// Material UI
import { Card, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton, Tooltip } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import InitializeIcon from "@mui/icons-material/PlayCircleOutline";

// API
import agentPromptsApi from "../../api/agentPrompts/agentPromptsApi";

function AgentPrompts() {
  const navigate = useNavigate();
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      setLoading(true);
      const response = await agentPromptsApi.getAllPrompts();
      setPrompts(response.prompts || []);
      setError(null);
    } catch (err) {
      console.error("Error fetching prompts:", err);
      setError("Failed to load agent prompts");
    } finally {
      setLoading(false);
    }
  };

  const handleInitializeDefaults = async () => {
    try {
      setLoading(true);
      await agentPromptsApi.initializeDefaults();
      setSuccess("Default prompts initialized successfully");
      await fetchPrompts(); // Refresh the list
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      console.error("Error initializing defaults:", err);
      setError("Failed to initialize default prompts");
    } finally {
      setLoading(false);
    }
  };

  const handleEditPrompt = (agentName) => {
    navigate(`/admin/agent-prompts/${agentName}`);
  };

  const agentDescriptions = {
    "intent_recognizer": "Classifies user messages into predefined intents (BOOK_FLIGHT, VIEW_BOOKINGS, etc.) using Gemini AI with pattern-matching fallback",
    "data_extractor": "Extracts structured flight booking data (origin, destination, dates, passengers) from natural language messages using Gemini AI with validation", 
    "general_travel_handler": "Generates conversational AI responses for non-flight travel queries using the 'MyVoya' personality via Gemini AI"
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
              <MDTypography variant="h6" color="white">
                AI Agent Prompts Management
              </MDTypography>
              <MDButton
                variant="outlined"
                color="white"
                size="small"
                startIcon={<InitializeIcon />}
                onClick={handleInitializeDefaults}
                disabled={loading}
              >
                Initialize Defaults
              </MDButton>
            </MDBox>

            <MDBox pt={3} px={2}>
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

              <MDTypography variant="body2" color="text" mb={2}>
                Manage prompts for AI agents that power the chat system. Each agent has a specific role and can be customized with different prompts.
              </MDTypography>

              {loading ? (
                <MDBox display="flex" justifyContent="center" p={3}>
                  <MDTypography variant="body2" color="text">
                    Loading agent prompts...
                  </MDTypography>
                </MDBox>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>
                          <MDTypography variant="caption" fontWeight="bold" color="text">
                            Agent Name
                          </MDTypography>
                        </TableCell>
                        <TableCell>
                          <MDTypography variant="caption" fontWeight="bold" color="text">
                            Goal/Purpose
                          </MDTypography>
                        </TableCell>
                        <TableCell>
                          <MDTypography variant="caption" fontWeight="bold" color="text">
                            Status
                          </MDTypography>
                        </TableCell>
                        <TableCell>
                          <MDTypography variant="caption" fontWeight="bold" color="text">
                            Last Updated
                          </MDTypography>
                        </TableCell>
                        <TableCell align="center">
                          <MDTypography variant="caption" fontWeight="bold" color="text">
                            Actions
                          </MDTypography>
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {prompts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} align="center">
                            <MDTypography variant="body2" color="text">
                              No agent prompts found. Click "Initialize Defaults" to create default prompts.
                            </MDTypography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        prompts.map((prompt) => (
                          <TableRow key={prompt.agent_name}>
                            <TableCell>
                              <MDTypography variant="body2" fontWeight="medium">
                                {prompt.agent_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </MDTypography>
                            </TableCell>
                            <TableCell style={{ maxWidth: '300px' }}>
                              <MDTypography variant="caption" color="text">
                                {prompt.goal || agentDescriptions[prompt.agent_name] || "No description available"}
                              </MDTypography>
                            </TableCell>
                            <TableCell>
                              <MDTypography
                                variant="caption"
                                color={prompt.is_active ? "success" : "error"}
                                fontWeight="medium"
                              >
                                {prompt.is_active ? "Active" : "Inactive"}
                              </MDTypography>
                            </TableCell>
                            <TableCell>
                              <MDTypography variant="caption" color="text">
                                {new Date(prompt.updated_at).toLocaleDateString()}
                              </MDTypography>
                            </TableCell>
                            <TableCell align="center">
                              <Tooltip title="Edit Prompt">
                                <IconButton
                                  size="small"
                                  onClick={() => handleEditPrompt(prompt.agent_name)}
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </MDBox>
          </Card>
        </MDBox>
      </MDBox>
    </DashboardLayout>
  );
}

export default AgentPrompts;