import { useEffect, useState } from "react";
import {
  Box,
  FormHelperText,
  Icon,
  IconButton,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { map } from "lodash";

const FileUploaderForArray = (props) => {
  const { formikProp, acceptType, name, size, maxFileUpload } = props;
  const [imageList, setImageList] = useState([]);

  useEffect(() => {
    const initialFiles = Array.isArray(formikProp.values[name])
      ? formikProp.values[name]
      : [];
    setImageList(initialFiles);
  }, [formikProp.values[name]]);

  const theme = useTheme();

  const onImageChange = (event) => {
    const files = Array.from(event.target.files);
    const existingFiles = Array.isArray(formikProp.values[name])
      ? [...formikProp.values[name]]
      : [];

    files.forEach((file) => {
      if (existingFiles.length < maxFileUpload) {
        existingFiles.push(file);
      }
    });

    formikProp.setFieldValue(name, existingFiles);
    setImageList(existingFiles);
  };

  const handleRemoveFile = (index) => {
    const updatedFiles = imageList.filter(
      (_, fileIndex) => fileIndex !== index
    );
    formikProp.setFieldValue(name, updatedFiles);
    setImageList(updatedFiles);
  };

  return (
    <Box>
      <input
        type="file"
        accept={acceptType}
        onChange={onImageChange}
        style={{ display: "none" }}
        id={name}
      />
      <label htmlFor={name}>
        <IconButton component="span" sx={{ p: 0 }}>
          <Icon color={theme.palette.primary.main}>cloud_upload</Icon>
          <Typography variant="body1" color="primary" sx={{ml:1}}>
            Upload Image
          </Typography>
        </IconButton>
      </label>
      <FormHelperText>
        {formikProp.touched[name] && formikProp.errors[name] && (
          <span style={{ color: "red" }}>{formikProp.errors[name]}</span>
        )}
      </FormHelperText>
      {map(imageList, (file, index) => (
        <Box
          key={index}
          display="flex"
          alignItems="center"
          justifyContent="space-between"
        >
          <Typography variant="body2">{file.name}</Typography>
          <IconButton onClick={() => handleRemoveFile(index)}>
            <Icon color="error">remove_circle</Icon>
          </IconButton>
        </Box>
      ))}
    </Box>
  );
};

export default FileUploaderForArray;
