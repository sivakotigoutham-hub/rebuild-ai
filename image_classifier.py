import streamlit as st
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import os
import traceback

CATEGORIES = [
    "Bricks",
    "Concrete Blocks",
    "Timber",
    "Tiles",
    "Steel",
    "Other Metal",
    "Sand",
    "Gravel",
    "Doors",
    "Windows",
    "Plumbing Fixtures",
    "Electrical Fixtures",
    "Other",
]

CATEGORY_LABELS = {
    "Bricks": ["bricks", "red bricks", "building bricks"],
    "Concrete Blocks": ["concrete blocks", "cement blocks"],
    "Timber": ["timber", "wood", "lumber", "oak", "beam"],
    "Tiles": ["tiles", "ceramic tiles", "floor tiles"],
    "Steel": ["steel", "metal beams", "steel beams"],
    "Other Metal": ["other metal", "copper", "aluminum", "iron"],
    "Sand": ["sand", "building sand"],
    "Gravel": ["gravel", "crushed stone"],
    "Doors": ["doors", "interior doors", "exterior doors"],
    "Windows": ["windows", "window frames"],
    "Plumbing Fixtures": ["plumbing fixtures", "pipes", "faucets"],
    "Electrical Fixtures": ["electrical fixtures", "outlets", "switches"],
    "Other": ["other materials", "miscellaneous"],
}


@st.cache_resource
def load_model():
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
    model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
    return processor, model


def classify_image(image, top_k=3):
    try:
        processor, model = load_model()
    except Exception as e:
        st.error(f"Failed to load CLIP model: {e}")
        return None, None

    try:
        labels = []
        for cat in CATEGORIES:
            cat_labels = CATEGORY_LABELS.get(cat, [cat])
            labels.extend(cat_labels)

        text_inputs = processor(text=labels, return_tensors="pt", padding=True)

        image_input = processor(images=image, return_tensors="pt")

        with torch.no_grad():
            logits_per_image, logits_per_text = model.forward(
                image_inputs=image_input["pixel_values"],
                text_inputs=text_inputs["input_ids"],
                attention_mask=text_inputs.get("attention_mask"),
            )

        probs = logits_per_image.softmax(dim=-1)[0]

        # Get top-k indices
        top_indices = torch.topk(probs, min(top_k, len(probs))).indices.tolist()
        top_scores = [float(probs[i]) for i in top_indices]

        results = []
        for idx in top_indices:
            label = labels[idx]
            score = top_scores.pop(0) if top_scores else 0
            # Find which category this label belongs to
            results.append((label, score))

        return results, labels

    except Exception as e:
        st.error(f"Inference failed: {e}")
        traceback.print_exc()
        return None, None


def get_top_three_categories(image):
    """Returns top 3 category suggestions with scores, or None if model fails."""
    results, all_labels = classify_image(image, top_k=3)
    if results is None:
        return None
    # Normalize: ensure we have exactly 3 results
    if len(results) < 3:
        # Pad with lowest possible score
        while len(results) < 3:
            results.append(("Other", 0.0))
    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:3]


def classify_image_manual(category_name):
    """Return the score for a manually selected category (placeholder score)."""
    return 70.0


def get_disclaimer():
    return "⚠️ Image recognition is an AI suggestion. Please confirm the category before saving."