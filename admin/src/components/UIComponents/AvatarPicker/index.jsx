import React, { useState } from "react";

import { useTheme } from "@mui/material";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";

import AvatarEditor from "react-avatar-editor";
import Dropzone from "react-dropzone";

const AvatarPicker = React.forwardRef((props, ref) => {
  const theme = useTheme();
  const { selectedImage } = props;
  const [imageSetting, setImageSetting] = useState({
    image: selectedImage ? selectedImage : null,
    scale: 1,
    borderRadius: 0,
    rotate: 0,
    backgroundColor: "transparent",
    position: { x: 0, y: 0 },
    editImage: "",
  });

  const handleDrop = (dropped) => {
    setImageSetting({
      ...imageSetting,
      image: dropped[0],
    });
  };

  const handleScale = (event) => {
    setImageSetting({
      ...imageSetting,
      scale: event.target.value,
    });
  };
  const handleBorderRadius = (event) => {
    setImageSetting({
      ...imageSetting,
      borderRadius: event.target.value,
    });
  };
  const handleRotate = (event) => {
    setImageSetting({
      ...imageSetting,
      rotate: event.target.value,
    });
  };
  const handlePositionChange = (position) => {
    setImageSetting({ ...imageSetting, position: position });
  };

  return (
    <>
      <Box sx={{ width: { sm: "380px", xs: "100%" }, p: { sm: 1 } }}>
        <Grid container spacing={{ sm: 2, xs: 1 }}>
          <Grid item xs={12}>
            <Box
              sx={{
                mb: 1,
                py: 1,
                borderBottom: `1px solid ${theme.palette.grey[300]}`,
              }}
            >
              <Dropzone onDrop={handleDrop} noKeyboard>
                {({ getRootProps, getInputProps }) => (
                  <div
                    {...getRootProps()}
                    style={{
                      width: "max-content",
                      margin: "auto auto",
                      position: "relative",
                    }}
                  >
                    <AvatarEditor
                      image={imageSetting.image}
                      scale={parseFloat(imageSetting.scale)}
                      rotate={parseFloat(imageSetting.rotate)}
                      position={imageSetting.position}
                      onPositionChange={handlePositionChange}
                      borderRadius={imageSetting.borderRadius}
                      disableHiDPIScaling={true}
                      border={0}
                      className="avatar-upload-canvas"
                      ref={ref}
                    />
                    <input {...getInputProps()} />
                    {imageSetting.image === null && (
                      <Box
                        sx={{
                          width: "100%",
                          position: "absolute",
                          zIndex: 10,
                          top: "50%",
                          left: "50%",
                          transform: "translate(-50%,-50%)",
                          textAlign: "center",
                          color: "grey.800",
                        }}
                      >
                        <Typography sx={{ mb: "4px" }}>
                          Click to Upload
                        </Typography>
                        <Typography sx={{ mb: "4px" }}>OR</Typography>
                        <Typography>Drag & Drop here</Typography>
                      </Box>
                    )}
                  </div>
                )}
              </Dropzone>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { sm: "1.5fr 2fr" },
                gridGap: { sm: "4px 16px", xs: "4px 8px" },
              }}
            >
              <Typography>Zoom :</Typography>
              <Box sx={{ px: 1 }}>
                <Slider
                  aria-label="Zoom"
                  valueLabelDisplay="auto"
                  step={0.1}
                  min={1}
                  max={10}
                  value={imageSetting.scale}
                  onChange={handleScale}
                />
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { sm: "1.5fr 2fr" },
                gridGap: "4px 16px",
              }}
            >
              <Typography>Rotation :</Typography>
              <Box sx={{ px: 1 }}>
                <Slider
                  aria-label="Rotation"
                  valueLabelDisplay="auto"
                  min={0}
                  max={360}
                  value={imageSetting.rotate}
                  onChange={handleRotate}
                />
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { sm: "1.5fr 2fr" },
                gridGap: "4px 16px",
              }}
            >
              <Typography>Border Radius :</Typography>
              <Box sx={{ px: 1 }}>
                <Slider
                  aria-label="Border Radius"
                  valueLabelDisplay="auto"
                  min={0}
                  max={200}
                  value={imageSetting.borderRadius}
                  onChange={handleBorderRadius}
                />
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </>
  );
});

export default AvatarPicker;
