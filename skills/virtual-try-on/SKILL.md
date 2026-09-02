---
name: virtual-try-on
description: Analyze a product image and a model image, optimize a fidelity-focused virtual try-on prompt, wait for explicit confirmation, and then generate one edited image with Codex built-in image generation. Use for clothing or wearable-product try-on requests, including requests that still need one required image; do not use for unrelated image compositing.
---

# Virtual Try-On

Create a faithful model try-on from exactly two inputs without using external APIs.

## Input contract

- Image 1 is the product image.
- Image 2 is the model image.
- Accept conversation attachments or explicit local file paths.
- If either image is missing, unreadable, or its role is ambiguous, identify the missing information and wait. Do not infer the role and do not generate.
- For local paths, inspect each target with `view_image` before continuing so both images are visible in conversation context.

## Stage 1: optimize and wait

Inspect only visible evidence in both images. Identify:

- Product: category, color, material, texture, pattern, text, Logo, silhouette, construction, and correct wearing location.
- Model: face and identity, hairstyle, pose, body proportions, existing occlusion, framing, background, and lighting.

Turn the user's request into one concise Chinese editing prompt. The prompt must state that Image 1 supplies the product and Image 2 supplies the person, pose, framing, background, and lighting. Preserve all visible product and model invariants. Allow only the fit, local deformation, occlusion, folds, perspective, contact shadows, and lighting integration required for physically plausible wear.

Do not invent hidden product details. Do not add clothing, accessories, text, Logo, patterns, people, or props. Do not change identity, face, age, hairstyle, body type, gender expression, pose, camera, crop, background, or overall lighting unless the user explicitly requests that specific change.

Respond with:

```text
优化后的换装提示词：
<final Chinese prompt>

请检查提示词。回复“确认生成”后，我才会调用内置生图；也可以直接告诉我需要修改的内容。
```

Stop after presenting the prompt. Never call image generation in the same turn as the first optimized prompt.

If the user changes any substantive requirement, revise the prompt and wait for confirmation again. A prior confirmation applies only to the exact latest prompt.

## Stage 2: generate once after confirmation

Continue only when the user explicitly confirms the latest prompt with “确认生成” or an unambiguous equivalent. One confirmation authorizes one generation call.

Use Codex built-in `imagegen` mode. Do not call Maibao, the local FastAPI app, an external API, or the GPT Image CLI.

Choose exactly one image reference mechanism:

- When every target image has a local path, pass both paths through `referenced_image_paths` in product-then-model order.
- When any target exists only as a conversation image, use the smallest `num_last_images_to_include` that contains both target images.
- Never provide both mechanisms. If neither mechanism can include both targets, ask the user to attach the missing images again.

Use the confirmed prompt as the main instruction and repeat the Image 1/Image 2 roles and preservation constraints. Make exactly one built-in generation call. Do not retry or create variants without a new confirmation.

Show the result inline and report:

- that Codex built-in image generation was used;
- the final confirmed prompt;
- the saved path only when the image is project-bound or the user requested a destination.

If a destination file already exists, create a versioned sibling unless the user explicitly authorizes replacement.

## Failure and iteration

- If built-in image generation is unavailable or fails, report the error and stop. Do not silently switch providers.
- If the result misses a requirement, describe the visible deviation and propose one targeted prompt change.
- Before another generation, present the revised prompt and obtain a new confirmation.
- Do not claim the built-in backend uses a specific API model ID.
