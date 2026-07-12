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
import { imageObj } from "../../services/Images";

const FileUploader = (props) => {
  const {
    formikProp,
    acceptType,
    name,
    size,
    maxFileUpload,
    setEmpty,
    isShowOnly,
    imageUrl="",
  } = props;

  const [imageList, setImageList] = useState([]);

  useEffect(() => {
    if (setEmpty) {
      setImageList([]);
    }
  }, [setEmpty]);

  const theme = useTheme();

  const onImageChange = (event) => {
    let fileArray = [];
    if (event.target.files.length > 0) {
      const files = event.target.files;
      const existingFiles = [...formikProp.values[name]];

      for (let i = 0; i < files.length; i++) {
        existingFiles.push(files[i]);
        formikProp.setFieldValue(name, [...existingFiles]);

        if (files[i].type.indexOf("image") > -1) {
          fileArray.push({
            type: "image",
            url: URL.createObjectURL(files[i]),
          });
        } else if (files[i].type.indexOf("video") > -1) {
          fileArray.push({
            type: "video",
            url: URL.createObjectURL(files[i]),
          });
        } else if (files[i].type.indexOf("application") > -1) {
          fileArray.push({
            type: "file",
            url: URL.createObjectURL(files[i]),
            name: files[i].name,
          });
        }
      }
    }
    setImageList([...imageList, ...fileArray]);
  };

  const handleRemoveFile = (index) => {
    const updatedFiles = imageList.filter(
      (file, fileIndex) => fileIndex !== index
    );
    const updatedFormikFiles = formikProp.values[name].filter(
      (file, fileIndex) => fileIndex !== index
    );

    setImageList(updatedFiles);
    formikProp.setFieldValue(name, updatedFormikFiles);
  };

  if (isShowOnly && imageUrl) {
    // Render the image in "show-only" mode
    return (
      <Box
        className="rounded position-relative overflow-hidden"
        sx={{
          width: size,
          height: size,
          boxShadow: theme.shadows[3],
        }}
      >
        <Box
          component="img"
          src={imageUrl}
          alt="Uploaded content"
          className="img-cover rounded"
          sx={{
            width: size,
            height: size,
          }}
        />
      </Box>
    );
  }

  return (
    <>
      {imageList.length > 0 &&
        map(imageList, (item, index) =>
          item.type === "image" ? (
            <Box
              key={index}
              className="rounded position-relative cursor-pointer overflow-hidden"
              sx={{
                "&::after": {
                  content: '""',
                  position: "absolute",
                  backgroundColor: "rgba(0,0,0,0.3)",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                },
              }}
            >
              <Box
                component="img"
                src={item.url}
                alt={`${item.type}_${index}`}
                className="img-cover rounded position-relative"
                sx={{
                  width: size,
                  height: size,
                }}
              />
              <IconButton
                sx={{
                  background: "rgba(255,255,255,.3)",
                  color: "primary.contrastText",
                  position: "absolute",
                  top: "8%",
                  right: "5%",
                  transform: "translate(-8%, -5%)",
                  zIndex: "2",
                  "&:hover": {
                    background: "rgba(255,255,255,.3)",
                    color: "primary.contrastText",
                  },
                }}
                onClick={() => handleRemoveFile(index)}
              >
                <Icon fontSize="small">close</Icon>
              </IconButton>
            </Box>
          ) : item.type === "video" ? (
            <video key={index} width="320" height="240" controls>
              <source src={item.url} type="video/mp4" />
            </video>
          ) : (
            <Box
              sx={{
                width: size,
                height: size,
                p: 1,
                boxShadow: theme.shadows[3],
              }}
              className="rounded position-relative d-flex flex-column gap-3 align-items-center justify-content-center cursor-pointer"
            >
              <Box
                component="img"
                src={imageObj.documentIcon}
                sx={{ width: 40 }}
              />
              <Typography variant="subtitle2" key={index}>
                {item.name}
              </Typography>
              <IconButton
                sx={{
                  background: theme.palette.grey[300],
                  color: "text.primary",
                  position: "absolute",
                  top: "8%",
                  right: "5%",
                  transform: "translate(-8%, -5%)",
                  zIndex: "2",
                  boxShadow: theme.shadows[2],
                  "&:hover": {
                    background: theme.palette.grey[300],
                    color: "text.primary",
                  },
                }}
                onClick={() => handleRemoveFile(index)}
              >
                <Icon fontSize="small">close</Icon>
              </IconButton>
            </Box>
          )
        )}
      {formikProp.values[name].length === maxFileUpload ? null : (
        <Box
          sx={{ border: `1px dashed #C4C4C4`, width: size, height: size }}
          className="rounded position-relative cursor-pointer d-inline-block"
          component="label"
        >
          <input
            hidden
            accept={acceptType ?? "image/*"}
            onChange={onImageChange}
            name={name}
            multiple
            type="file"
          />

          <Box
            component="img"
            src={imageObj.uploadIcon}
            sx={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 50,
              height: 50,
            }}
          />
        </Box>
      )}

      <FormHelperText className="w-100" error>
        {formikProp.errors[name]}
      </FormHelperText>
    </>
  );
};

export default FileUploader;
