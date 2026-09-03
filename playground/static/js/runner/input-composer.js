export function bindInputComposer(form, onSubmit, { clearAttachments } = {}) {
  const messageInput = form?.querySelector("textarea[name='message']");
  const submitButton = form?.querySelector("button[type='submit']");
  // A disabled submit button stops the click and nothing else: requestSubmit()
  // sends the form anyway, so Enter kept queueing questions while an answer was
  // still being written. The button is the state; this makes every path read it.
  const isBusy = () => Boolean(submitButton?.disabled);

  messageInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
      return;
    }
    event.preventDefault();
    if (isBusy()) {
      return;
    }
    form.requestSubmit();
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (isBusy()) {
      return;
    }
    const formData = new FormData(form);
    const files = Array.from(formData.getAll("attachments"))
      .filter((item) => item instanceof File && item.name);
    const payload = {
      message: String(formData.get("message") || ""),
      attachment_names: files.map((file) => file.name),
      attachments: await Promise.all(files.map(fileToAttachment)),
    };
    const displayAttachments = files.map(fileToDisplayAttachment);
    if (messageInput) {
      messageInput.value = "";
    }
    clearAttachments?.();
    onSubmit?.({ ...payload, displayAttachments });
  });
}

function fileToDisplayAttachment(file) {
  return {
    kind: file.type.startsWith("image/") ? "image" : "file",
    name: file.name,
    media_type: file.type || "application/octet-stream",
    size: file.size,
    preview_url: file.type.startsWith("image/") ? URL.createObjectURL(file) : "",
  };
}

function fileToAttachment(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const mediaType = file.type || "application/octet-stream";
      resolve({
        kind: mediaType.startsWith("image/") ? "image" : "file",
        name: file.name,
        media_type: mediaType,
        content: String(reader.result || ""),
        metadata: { size: file.size },
      });
    });
    reader.addEventListener("error", () => reject(reader.error || new Error("附件讀取失敗。")));
    reader.readAsDataURL(file);
  });
}
