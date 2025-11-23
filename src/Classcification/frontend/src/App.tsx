"use client";

import {
  Button,
  Flex,
  RadioGroup,
  VStack,
  HStack,
  Text,
  Image,
  Progress,
  Box,
  AspectRatio,
} from "@chakra-ui/react";
import { useState, useEffect } from "react";
import { MdAdsClick, MdInfo } from "react-icons/md";

const params = new URLSearchParams(window.location.search);
const task = params.get("task") || "spin_val_part";
const category = params.get("category");
const groupIndex = parseInt(params.get("groupIndex") || "0", 10);
const sandbox = params.get("sandbox") || "True";
const review = params.get("review") || "false";
const assignmentId = params.get("assignmentId");
const workerId = params.get("workerId");
const hitId = params.get("hitId");

const handleSubmitToMTurk = (submissionData: {
  answers: Record<number, string>;
  issueTexts: Record<number, string>;
  userFeedback?: string;
}) => {
  const form = document.createElement("form");
  form.method = "POST";

  console.log(window.location.hostname);
  console.log("Submitting to MTurk with sandbox:", sandbox);
  // lower sandbox
  let sandbox_string = sandbox.toString();
  // lower sandbox_string
  sandbox_string = sandbox_string.toLowerCase();
  console.log("Lowered sandbox string:", sandbox_string);
  const isSandbox = sandbox_string === "true";
  form.action = isSandbox
    ? "https://workersandbox.mturk.com/mturk/externalSubmit"
    : "https://www.mturk.com/mturk/externalSubmit";

  form.appendChild(
    Object.assign(document.createElement("input"), {
      name: "assignmentId",
      value: assignmentId,
      type: "hidden",
    }),
  );

  // (Optional) You can add other fields like workerId, HITId, custom responses
  // But MTurk requires only assignmentId
  form.appendChild(
    Object.assign(document.createElement("input"), {
      name: "workerId",
      value: workerId,
      type: "hidden",
    }),
  );
  form.appendChild(
    Object.assign(document.createElement("input"), {
      name: "hitId",
      value: hitId,
      type: "hidden",
    }),
  );
  form.appendChild(
    Object.assign(document.createElement("input"), {
      name: "task",
      value: task,
      type: "hidden",
    }),
  );
  form.appendChild(
    Object.assign(document.createElement("input"), {
      name: "submissionData",
      value: JSON.stringify(submissionData), // Convert submission data to JSON string
      type: "hidden",
    }),
  );
  console.log("Submitting form to MTurk:", form);
  document.body.appendChild(form);
  form.submit();
};

// check if deploy or local and set base URL accordingly
const isDeploy = window.location.hostname !== "localhost";
const BASE_URL = isDeploy
  ? "https://instancespot-backend-f94efee7f52c.herokuapp.com/api"
  : "http://127.0.0.1:8000/api";

const App = () => {
  const [entryIds, setEntryIds] = useState<number[]>([]);
  const [caseIndex, setCaseIndex] = useState(0);
  const [imageUrl, setImageUrl] = useState("");
  const [categoryName, setCategoryName] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [value, setValue] = useState<string | null>(null);
  const [maskUrl, setMaskUrl] = useState<string>("");
  const [showMask, setShowMask] = useState<boolean>(true);
  const [naturalSize, setNaturalSize] = useState({ width: 4, height: 3 }); // default 4:3
  const [issueTexts, setIssueTexts] = useState<Record<number, string>>({});
  const [currentIssueText, setCurrentIssueText] = useState<string>("");
  const [showInstructionModal, setShowInstructionModal] =
    useState<boolean>(false);
  const [userFeedback, setUserFeedback] = useState<string>("");
  const [showFeedbackModal, setShowFeedbackModal] = useState<boolean>(false);
  const ratio = naturalSize.width / naturalSize.height;
  const count = entryIds.length;

  useEffect(() => {
    console.log(
      `Fetching task IDs with parameters: {
        task: ${task},
        category: ${category},
        groupIndex: ${groupIndex},
        sandbox: ${sandbox == "True"},
        review: ${review},
        assignmentId: ${assignmentId}
      }`,
    );
    fetch(
      `${BASE_URL}/tasks/?task=${task}&category=${category}&groupIndex=${groupIndex}&sandbox=${
        sandbox == "True"
      }&review=${review}&assignmentId=${assignmentId}`,
    )
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch task IDs");
        return res.json();
      })
      .then((data) => {
        setEntryIds(data["entry_ids"]); // Store list of entry_ids
        // for each caseIndex set the answers, answer is an array
        if (review === "True") {
          const initialAnswers: Record<number, string> = {};
          data["answers"].forEach((answer: string, index: number) => {
            initialAnswers[index] = answer.toString(); // Convert answer to string
          });
          setAnswers(initialAnswers); // Initialize answers with fetched data
          console.log("Fetched entry IDs:", data["entry_ids"]);
          console.log("Initial answers:", initialAnswers);
        }
      })
      .catch((err) => console.error("Task IDs fetch error:", err));
  }, []);

  // Mock loading logic for mask + category
  useEffect(() => {
    if (entryIds.length === 0) return;

    const entry_id = entryIds[caseIndex];
    setShowMask(true); // Reset mask visibility on new case
    setValue(answers[caseIndex] ?? null);
    setCurrentIssueText(issueTexts[caseIndex] ?? "");
    fetch(
      `${BASE_URL}/image/?task=${task}&category=${category}&entry_id=${entry_id}`,
    )
      .then((res) => {
        if (!res.ok) throw new Error("Image not found");
        return res.json();
      })
      .then((data) => {
        setImageUrl(data.image_url);
      })
      .catch((err) => console.error("Image error:", err));

    if (category != null && (task == "agreeTest" || task == "main")) {
      setCategoryName(category);
    } else if (category != null) {
      fetch(`${BASE_URL}/category/?task=${task}&entry_id=${entry_id}`)
        .then((res) => res.json())
        .then((json) => {
          setCategoryName(json.name);
        })
        .catch((err) => console.error("Category error:", err));
    }

    fetch(
      `${BASE_URL}/mask/?task=${task}&category=${category}&entry_id=${entry_id}`,
    )
      .then((res) => {
        if (!res.ok) throw new Error("Mask not found");
        return res.blob();
      })
      .then((blob) => setMaskUrl(URL.createObjectURL(blob)))
      .catch((err) => {
        console.error("Mask error:", err);
        setMaskUrl("");
      });
  }, [entryIds, caseIndex, answers, issueTexts]);

  const handleNext = () => {
    if (caseIndex < count - 1) {
      setCaseIndex(caseIndex + 1);
    } else {
      // On last case, check if feedback modal should be shown
      if (!showFeedbackModal) {
        setShowFeedbackModal(true);
      }
    }
  };

  const handlePrevious = () => {
    if (caseIndex > 0) {
      setCaseIndex(caseIndex - 1);
    }
  };

  const handleAnswerChange = (val: string | null) => {
    setValue(val);
    setAnswers((prev) => ({
      ...prev,
      [caseIndex]: val ?? "", // Store answer for current case
    }));

    // If not "Something is wrong", clear the issue text for this case
    if (val !== "-1") {
      setIssueTexts((prev) => {
        const updated = { ...prev };
        delete updated[caseIndex];
        return updated;
      });
      setCurrentIssueText("");
    }

    // Show feedback modal when the last question is answered
    if (caseIndex === count - 1 && val !== null) {
      setShowFeedbackModal(true);
    }

    console.log(`Answer for case ${caseIndex}: ${val}`);
  };

  const handleIssueTextChange = (text: string) => {
    setCurrentIssueText(text);
    setIssueTexts((prev) => ({
      ...prev,
      [caseIndex]: text,
    }));
  };

  const handleFeedbackSubmit = () => {
    setShowFeedbackModal(false);
    // Proceed with the actual submission
    console.log("Submitting answers:", answers);
    console.log("Submitting issue texts:", issueTexts);
    console.log("Submitting user feedback:", userFeedback);
    const submissionData = {
      answers,
      issueTexts,
      userFeedback,
    };
    handleSubmitToMTurk(submissionData);
    alert("HIT completed! Thank you for your participation!");
  };

  return (
    <Flex
      gap="4"
      direction="column"
      width={"100vw"}
      height={"100vh"}
      backgroundColor={"#F2F3F3"}
      alignItems="center"
      p={4}
    >
      <Progress.Root
        maxW="480px"
        minW={"320px"}
        width={"30%"}
        size={"lg"}
        colorPalette="blue"
        value={caseIndex + 1}
        max={count}
      >
        <HStack gap="5" alignItems="center">
          <Progress.Label color={"black"}>
            {caseIndex + 1} of {count}
          </Progress.Label>
          <Progress.Track flex="1">
            <Progress.Range />
          </Progress.Track>
          <Progress.Label color={"black"}>HIT</Progress.Label>
        </HStack>
      </Progress.Root>

      {/* Image + Question Panel */}
      <Flex
        justifyContent={"space-around"}
        alignItems={"center"}
        width="100%"
        height={"85%"}
      >
        {/* Image Area */}
        <div
          style={{
            padding: "16px",
            width: "75%",
            height: "90%",
          }}
        >
          <Image
            src={imageUrl}
            alt="hidden preload"
            display="none"
            onLoad={(e) => {
              const { naturalWidth, naturalHeight } = e.currentTarget;
              setNaturalSize({ width: naturalWidth, height: naturalHeight });
            }}
          />

          {/* Hide/Show Overlay Button - Top Right */}
          <Box display="flex" justifyContent="flex-end">
            <Button
              variant={showMask ? "subtle" : "solid"}
              size="sm"
              colorPalette={showMask ? "gray" : "blue"}
              aria-pressed={showMask}
              onClick={() => setShowMask((prev) => !prev)}
            >
              <MdAdsClick /> {showMask ? "Hide Overlay" : "Show Overlay"}
            </Button>
          </Box>

          {/* Two images side by side */}
          <Flex gap="4" width="100%" height="100%">
            {/* Original Image (Left) */}
            <Box width="50%" height="100%">
              <Text
                fontSize="sm"
                fontWeight="bold"
                color="gray.700"
                mb="2"
                textAlign="center"
              >
                Original Image
              </Text>
              <AspectRatio ratio={ratio} width="100%" height="95%">
                <Box
                  position="relative"
                  border="2px solid #aaa"
                  borderRadius="md"
                >
                  <Image
                    src={imageUrl}
                    alt="Original image"
                    width="100%"
                    height="100%"
                    objectFit="contain"
                    borderRadius="md"
                  />
                </Box>
              </AspectRatio>
            </Box>

            {/* Image with Overlay (Right) */}
            <Box width="50%" height="100%">
              <Text
                fontSize="sm"
                fontWeight="bold"
                color="gray.700"
                mb="2"
                textAlign="center"
              >
                {showMask
                  ? "Overlay with Segmentations (red region)"
                  : "Original Image"}
              </Text>
              <AspectRatio ratio={ratio} width="100%" height="95%">
                <Box
                  position="relative"
                  border="3px solid #3182ce"
                  borderRadius="md"
                >
                  <Image
                    src={imageUrl}
                    alt="Main image"
                    width="100%"
                    height="100%"
                    objectFit="contain"
                    borderRadius="md"
                  />
                  {showMask && maskUrl && (
                    <Image
                      src={maskUrl}
                      alt="Mask overlay"
                      position="absolute"
                      top="0"
                      left="0"
                      width="100%"
                      height="100%"
                      objectFit="contain"
                      opacity={0.5}
                      pointerEvents="none"
                      borderRadius="md"
                    />
                  )}
                </Box>
              </AspectRatio>
            </Box>
          </Flex>
        </div>

        {/* Question Area */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            width: "20%",
            height: "70%",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "center",
              width: "100%",
              height: "10%",
              marginTop: "-2%",
            }}
          >
            <Button
              variant="solid"
              size="sm"
              width="60%"
              colorPalette="blue"
              onClick={() => setShowInstructionModal(true)}
            >
              <MdInfo /> Instructions
            </Button>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
              width: "100%",
              height: value === "-1" ? "70%" : "50%",
              minHeight: value === "-1" ? "350px" : "250px",
              backgroundColor: "#ffffff",
              padding: "16px",
              transition: "height 0.3s ease, min-height 0.3s ease",
            }}
          >
            <Text fontWeight="semibold" textStyle="md" color={"gray.700"}>
              How many <strong>{categoryName}</strong> instances can you see in
              the segmented areas?
            </Text>
            <RadioGroup.Root
              value={value}
              onValueChange={(e) => handleAnswerChange(e.value)}
              colorPalette={"blue"}
            >
              <VStack
                gap="2.5"
                alignItems="flex-start"
                maxHeight="200px"
                mt={3}
              >
                {items.map((item) => (
                  <RadioGroup.Item
                    key={item.value}
                    value={item.value}
                    disabled={review === "True"}
                  >
                    {" "}
                    <RadioGroup.ItemHiddenInput />
                    <RadioGroup.ItemIndicator />
                    <RadioGroup.ItemText
                      textStyle="md"
                      fontWeight="semibold"
                      color={"gray.700"}
                    >
                      {item.label}
                    </RadioGroup.ItemText>
                  </RadioGroup.Item>
                ))}
              </VStack>
            </RadioGroup.Root>

            {/* Show text area only when "Something is wrong" is selected */}
            {value === "-1" && (
              <Box mt={4} width="100%">
                <Text fontSize="sm" fontWeight="medium" color="gray.600" mb={2}>
                  Please describe the issue:
                </Text>
                <textarea
                  placeholder="Describe the issue you encountered (e.g., image is unclear, object is partially hidden, loading error, etc.)"
                  value={currentIssueText}
                  onChange={(e) => handleIssueTextChange(e.target.value)}
                  disabled={review === "True"}
                  style={{
                    width: "100%",
                    minHeight: "80px",
                    padding: "8px",
                    border: "1px solid #ccc",
                    borderRadius: "4px",
                    fontSize: "14px",
                    fontFamily: "inherit",
                    resize: "vertical",
                    outline: "none",
                    backgroundColor: review === "True" ? "#f5f5f5" : "white",
                    color: "black",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#3182ce";
                    e.target.style.boxShadow = "0 0 0 1px #3182ce";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "#ccc";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </Box>
            )}
          </div>
        </div>
      </Flex>

      {/* User Feedback Box - Only show on last case */}

      {/* Navigation Buttons */}
      <Flex
        justifyContent={"flex-end"}
        width="100%"
        marginRight={"10%"}
        height={"10vh"}
      >
        <Button
          onClick={handlePrevious}
          disabled={caseIndex === 0}
          color={"#f3f3f3"}
          colorPalette="orange"
          width={"120px"}
        >
          ◀ Previous
        </Button>
        <Button
          colorPalette="orange"
          ml={4}
          color={"#f3f3f3"}
          onClick={handleNext}
          disabled={
            !value ||
            (value === "-1" && !currentIssueText.trim() && review !== "True")
          }
          width={"120px"}
          marginLeft={"2%"}
        >
          {caseIndex === count - 1 ? "Submit HIT" : "Next ▶"}
        </Button>
      </Flex>

      {/* Instruction Modal */}
      {showInstructionModal && (
        <Box
          position="fixed"
          top="0"
          left="0"
          width="100vw"
          height="100vh"
          backgroundColor="rgba(0, 0, 0, 0.5)"
          display="flex"
          alignItems="center"
          justifyContent="center"
          zIndex="9999"
          onClick={() => setShowInstructionModal(false)}
        >
          <Box
            backgroundColor="white"
            padding="6"
            borderRadius="lg"
            boxShadow="xl"
            maxWidth="600px"
            width="90%"
            maxHeight="80vh"
            overflowY="auto"
            onClick={(e) => e.stopPropagation()}
          >
            <Flex justifyContent="space-between" alignItems="center" mb="4">
              <Text fontSize="xl" fontWeight="bold" color="gray.800">
                Task Instructions
              </Text>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowInstructionModal(false)}
                colorPalette="gray"
              >
                ✕
              </Button>
            </Flex>

            {/* note change here for the Quick Reference */}
            <Box mb="4" p="3" backgroundColor="blue.50" borderRadius="md">
              <Text fontSize="sm" color="blue.600" mb="2" fontWeight="medium">
                📋 Quick Reference:
              </Text>
              <Text
                fontSize="sm"
                color="blue.600"
                textDecoration="underline"
                cursor="pointer"
                onClick={() =>
                  window.open(
                    "https://spin-instance.s3.us-east-2.amazonaws.com/Quadruped.pdf",
                    "_blank",
                  )
                }
              >
                View Quadruped Category References (PDF)
              </Text>
            </Box>

            <Box>
              <Text fontSize="md" lineHeight="1.6" mb="4" color="gray.700">
                This task entails indicating for each segmented region on an
                image whether it contains one or multiple instances of the
                specified category. You must choose between three choices for
                each segmented image:
              </Text>

              <VStack alignItems="flex-start" gap="4">
                <Box>
                  <Text fontWeight="bold" mb="2" color="gray.800">
                    One [instance]:
                  </Text>
                  <Text color="gray.600" mb="2">
                    Only one instance of the category is contained in the
                    segmentation, as shown for the two examples below.
                  </Text>
                  {/* Visual Example for One Object */}

                  <Box
                    mt="3"
                    p="3"
                    backgroundColor="green.50"
                    borderRadius="md"
                    borderLeft="3px solid"
                    borderColor="green.400"
                  >
                    <Flex gap="3" alignItems="center">
                      <Box
                        width="200px"
                        height="140px"
                        backgroundColor="gray.200"
                        borderRadius="md"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        border="2px dashed gray.400"
                      >
                        <Image
                          src={
                            "https://spin-instance.s3.us-east-2.amazonaws.com/snake_one.png"
                          }
                          alt="One Instance Example, snake"
                          width="200px"
                          height="140px"
                          objectFit="cover"
                          borderRadius="md"
                        />
                      </Box>
                      <Text fontSize="sm" color="green.700" fontWeight="medium">
                        ✓ One instance of Snake-Torso-Belly
                      </Text>
                    </Flex>
                  </Box>
                  <Box
                    mt="3"
                    p="3"
                    backgroundColor="green.50"
                    borderRadius="md"
                    borderLeft="3px solid"
                    borderColor="green.400"
                  >
                    <Flex gap="3" alignItems="center">
                      <Box
                        width="200px"
                        height="140px"
                        backgroundColor="gray.200"
                        borderRadius="md"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        border="2px dashed gray.400"
                      >
                        <Image
                          src={
                            "https://spin-instance.s3.us-east-2.amazonaws.com/snake_eye.png"
                          }
                          alt="One Object Example"
                          width="200px"
                          height="140px"
                          objectFit="cover"
                          borderRadius="md"
                        />
                      </Box>
                      <Text fontSize="sm" color="green.700" fontWeight="medium">
                        ✓ One instance of Snake-Head-Eyes
                      </Text>
                    </Flex>
                  </Box>
                </Box>

                <Box>
                  <Text fontWeight="bold" mb="2" color="gray.800">
                    More than one [instance]:
                  </Text>
                  <Text color="gray.600" mb="2">
                    Multiple instances of the category are contained in the
                    segmentation, as shown for the two examples below.
                  </Text>
                  <Text
                    fontSize="sm"
                    color="gray.500"
                    mb="3"
                    fontStyle="italic"
                  >
                    Note: Choose this option when you can clearly identify
                    multiple separate instances of the same part type within the
                    highlighted segmentation area. Each instance should be a
                    distinct, individual occurrence of the specified category.
                  </Text>

                  {/* Visual Example for Multiple Objects */}
                  <Box
                    mt="3"
                    p="3"
                    backgroundColor="green.50"
                    borderRadius="md"
                    borderLeft="3px solid"
                    borderColor="green.400"
                  >
                    <Flex gap="3" alignItems="center">
                      <Box
                        width="200px"
                        height="140px"
                        backgroundColor="gray.200"
                        borderRadius="md"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        border="2px dashed gray.400"
                      >
                        <Image
                          src={
                            "https://spin-instance.s3.us-east-2.amazonaws.com/car_two.png"
                          }
                          alt="Two car doors examples"
                          width="200px"
                          height="140px"
                          objectFit="cover"
                          borderRadius="md"
                        />
                      </Box>
                      <Text fontSize="sm" color="green.700" fontWeight="medium">
                        ✓ Multiple instances of Car-Body-Door
                      </Text>
                    </Flex>
                    <Text
                      fontSize="xs"
                      color="gray.600"
                      mt="2"
                      fontStyle="italic"
                    >
                      This segmentation contains two separate car doors - each
                      door is a distinct instance of the "Car-Body-Door"
                      category.
                    </Text>
                  </Box>
                  <Box
                    mt="3"
                    p="3"
                    backgroundColor="green.50"
                    borderRadius="md"
                    borderLeft="3px solid"
                    borderColor="green.400"
                  >
                    <Flex gap="3" alignItems="center">
                      <Box
                        width="200px"
                        height="140px"
                        backgroundColor="gray.200"
                        borderRadius="md"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        border="2px dashed gray.400"
                      >
                        <Image
                          src={
                            "https://spin-instance.s3.us-east-2.amazonaws.com/quadruped_foot.png"
                          }
                          alt="One Object Example"
                          width="200px"
                          height="140px"
                          objectFit="fill"
                          borderRadius="md"
                        />
                      </Box>
                      <Text fontSize="sm" color="green.700" fontWeight="medium">
                        ✓ Multiple Instances of Quadruped-Foot
                      </Text>
                    </Flex>
                    <Text
                      fontSize="xs"
                      color="gray.600"
                      mt="2"
                      fontStyle="italic"
                    >
                      This example shows two instances of ‘Quadruped-Foot,’ with
                      each instance represented by a separate segmentation mask.
                    </Text>
                  </Box>
                </Box>

                <Box>
                  <Text fontWeight="bold" mb="2" color="gray.800">
                    Cannot Answer:
                  </Text>
                  <Text color="gray.600">
                    This option is available when you are not able to complete
                    the task. In these cases, please specify why in the text box
                    that will appear.
                  </Text>
                </Box>
              </VStack>

              <Box mt="4" p="3" backgroundColor="gray.50" borderRadius="md">
                <Text fontSize="sm" color="gray.600" mb="2">
                  For more detailed walkthrough of our UI and task, visit:
                </Text>
                <Text
                  fontSize="sm"
                  color="blue.600"
                  textDecoration="underline"
                  cursor="pointer"
                  onClick={() =>
                    window.open(
                      "https://spin-instance.s3.us-east-2.amazonaws.com/SPIN-Instance+Training.pdf",
                      "_blank",
                    )
                  }
                >
                  Click here for additional examples
                </Text>
              </Box>

              <Flex justifyContent="flex-end" mt="6">
                <Button
                  colorPalette="blue"
                  onClick={() => setShowInstructionModal(false)}
                >
                  Got it!
                </Button>
              </Flex>
            </Box>
          </Box>
        </Box>
      )}

      {/* Feedback Modal */}
      {showFeedbackModal && (
        <Box
          position="fixed"
          top="0"
          left="0"
          width="100vw"
          height="100vh"
          backgroundColor="rgba(0, 0, 0, 0.5)"
          display="flex"
          alignItems="center"
          justifyContent="center"
          zIndex="9999"
        >
          <Box
            backgroundColor="white"
            padding="6"
            borderRadius="lg"
            boxShadow="xl"
            maxWidth="500px"
            width="90%"
            maxHeight="70vh"
            overflowY="auto"
          >
            <Flex justifyContent="space-between" alignItems="center" mb="4">
              <Text fontSize="xl" fontWeight="bold" color="gray.800">
                📝 Your Feedback
              </Text>
            </Flex>

            <Box>
              <Text fontSize="md" lineHeight="1.6" mb="4" color="gray.700">
                Thank you for completing this task! Your feedback helps us
                improve the experience.
              </Text>

              <Text fontSize="sm" fontWeight="medium" color="gray.600" mb="3">
                Please share any comments, suggestions, or issues you
                encountered (optional):
              </Text>

              <textarea
                placeholder="Your feedback helps us improve the task experience..."
                value={userFeedback}
                onChange={(e) => setUserFeedback(e.target.value)}
                style={{
                  width: "100%",
                  minHeight: "120px",
                  padding: "12px",
                  border: "1px solid #ccc",
                  borderRadius: "8px",
                  fontSize: "14px",
                  fontFamily: "inherit",
                  resize: "vertical",
                  outline: "none",
                  backgroundColor: "white",
                  color: "black",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#3182ce";
                  e.target.style.boxShadow = "0 0 0 1px #3182ce";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "#ccc";
                  e.target.style.boxShadow = "none";
                }}
              />

              <Flex justifyContent="center" mt="6">
                <Button
                  colorPalette="blue"
                  onClick={handleFeedbackSubmit}
                  width="200px"
                >
                  Submit
                </Button>
              </Flex>
            </Box>
          </Box>
        </Box>
      )}
    </Flex>
  );
};

const items = [
  { label: "One", value: "0" },
  { label: "More than one", value: "1" },
  { label: "Cannot answer", value: "-1" },
];

export default App;
